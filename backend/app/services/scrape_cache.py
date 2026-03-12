"""Background scrape cache.

Runs one asyncio task that refreshes all book scrapers on a fixed interval.
After each full refresh, runs a two-pass arb verification:
  1. Detect candidate (event_id, market) pairs from the full line set.
  2. Re-scrape only the books involved in those candidates.
  3. Re-run arb detection on the fresh subset — only confirmed arbs are served.

The FastAPI endpoints read from the in-memory snapshot (instant).
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.scrapers.base import BookScraper

from app.models.odds import MarketLine

logger = logging.getLogger(__name__)


@dataclass
class BookStatus:
    book: str
    display_name: str
    logged_in: bool = False
    last_scraped_at: datetime | None = None
    last_error: str | None = None
    line_count: int = 0
    sport_counts: dict[str, int] = field(default_factory=dict)


class ScrapeCache:
    def __init__(
        self,
        interval_seconds: int = 60,
        playwright_interval_seconds: int = 90,
        api_interval_seconds: int = 20,
    ) -> None:
        self._interval = interval_seconds  # legacy fallback (unused when split loops active)
        self._playwright_interval = playwright_interval_seconds
        self._api_interval = api_interval_seconds
        self._lines: list[MarketLine] = []
        # Lines confirmed by two-pass verification; served to the frontend
        self._verified_lines: list[MarketLine] = []
        self._status: dict[str, BookStatus] = {}
        self._lock = asyncio.Lock()
        self._tasks: list[asyncio.Task] = []
        self._scrapers: list[BookScraper] = []

    def start(self, scrapers: list[BookScraper]) -> None:
        self._scrapers = scrapers
        for scraper in scrapers:
            self._status[scraper.book_name] = BookStatus(
                book=scraper.book_name,
                display_name=scraper.display_name,
            )
        playwright = [s for s in scrapers if s.scrape_type == "playwright"]
        api = [s for s in scrapers if s.scrape_type == "api"]
        # Run two independent loops: fast API loop + slower Playwright loop
        if playwright:
            self._tasks.append(asyncio.create_task(self._playwright_loop(playwright)))
        if api:
            self._tasks.append(asyncio.create_task(self._api_loop(api)))
        # Fallback: if all scrapers are one type, verification still runs via api loop;
        # if only playwright, run a combined loop
        if playwright and not api:
            self._tasks.clear()
            self._tasks.append(asyncio.create_task(self._combined_loop(playwright)))

    def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()

    async def get_lines(self) -> list[MarketLine]:
        """Return the verified line snapshot, falling back to all lines if verification not yet run."""
        async with self._lock:
            if self._verified_lines:
                return list(self._verified_lines)
            return list(self._lines)

    async def get_all_lines(self) -> list[MarketLine]:
        """Return all scraped lines (unfiltered)."""
        async with self._lock:
            return list(self._lines)

    async def get_status(self) -> dict[str, BookStatus]:
        async with self._lock:
            return dict(self._status)

    async def refresh_book(self, book_name: str) -> None:
        scraper = next((s for s in self._scrapers if s.book_name == book_name), None)
        if scraper is None:
            return
        await self._scrape_one(scraper)

    async def _playwright_loop(self, scrapers: list[BookScraper]) -> None:
        """Slow loop for browser-based scrapers (~90s per cycle). No verification — api loop handles it."""
        while True:
            tasks = [self._scrape_one(s) for s in scrapers]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("[playwright-loop] Cycle complete, sleeping %ds", self._playwright_interval)
            await asyncio.sleep(self._playwright_interval)

    async def _api_loop(self, scrapers: list[BookScraper]) -> None:
        """Fast loop for Kambi API scrapers (~9s per cycle). Runs verification after each refresh."""
        while True:
            tasks = [self._scrape_one(s) for s in scrapers]
            await asyncio.gather(*tasks, return_exceptions=True)
            await self._verify_and_store()
            logger.info("[api-loop] Cycle complete, sleeping %ds", self._api_interval)
            await asyncio.sleep(self._api_interval)

    async def _combined_loop(self, scrapers: list[BookScraper]) -> None:
        """Fallback loop used when only Playwright scrapers are configured."""
        while True:
            tasks = [self._scrape_one(s) for s in scrapers]
            await asyncio.gather(*tasks, return_exceptions=True)
            await self._verify_and_store()
            await asyncio.sleep(self._playwright_interval)

    async def _refresh_all(self) -> None:
        tasks = [self._scrape_one(scraper) for scraper in self._scrapers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _scrape_one(self, scraper: BookScraper) -> None:
        from app.scrapers.base import SessionExpiredError

        try:
            new_lines: list[MarketLine] = await asyncio.to_thread(scraper.scrape_all_sports)
        except SessionExpiredError:
            logger.warning("[%s] Session expired — attempting re-login", scraper.book_name)
            try:
                await asyncio.to_thread(scraper.login_and_save_session)
                new_lines = await asyncio.to_thread(scraper.scrape_all_sports)
            except Exception as exc:
                logger.error("[%s] Re-login failed: %s", scraper.book_name, exc)
                async with self._lock:
                    self._status[scraper.book_name].last_error = str(exc)
                    self._status[scraper.book_name].logged_in = False
                return
        except Exception as exc:
            logger.error("[%s] Scrape error: %s", scraper.book_name, exc, exc_info=True)
            async with self._lock:
                self._status[scraper.book_name].last_error = str(exc)
                self._status[scraper.book_name].logged_in = False
            return

        sport_counts: dict[str, int] = {}
        for line in new_lines:
            sport_counts[line.sport] = sport_counts.get(line.sport, 0) + 1

        async with self._lock:
            # Fix: compare against display_name, not book_name slug
            self._lines = [
                l for l in self._lines if l.book != scraper.display_name
            ] + new_lines
            self._status[scraper.book_name] = BookStatus(
                book=scraper.book_name,
                display_name=scraper.display_name,
                logged_in=True,
                last_scraped_at=datetime.now(timezone.utc),
                last_error=None,
                line_count=len(new_lines),
                sport_counts=sport_counts,
            )
        logger.info("[%s] Scraped %d lines", scraper.book_name, len(new_lines))

    # ------------------------------------------------------------------ #
    # Two-pass arb verification                                           #
    # ------------------------------------------------------------------ #

    async def _verify_and_store(self) -> None:
        """Re-scrape books involved in candidate arbs, then confirm."""
        from app.arb.engine import find_arb_keys

        async with self._lock:
            current_lines = list(self._lines)

        arb_keys = find_arb_keys(current_lines)
        if not arb_keys:
            logger.info("[verify] No arb candidates — skipping re-scrape")
            async with self._lock:
                self._verified_lines = current_lines
            return

        logger.info("[verify] %d candidate arb key(s) — re-scraping involved books", len(arb_keys))

        # Find which books appear in each candidate key
        books_to_rescrape = self._get_books_for_keys(current_lines, arb_keys)
        logger.info("[verify] Re-scraping: %s", sorted(books_to_rescrape))

        # Re-scrape only the involved books
        fresh_lines = await self._scrape_books_by_name(books_to_rescrape)

        # Merge: replace lines for re-scraped books with fresh data; keep others
        merged = [l for l in current_lines if l.book not in self._display_names(books_to_rescrape)]
        merged.extend(fresh_lines)

        # Re-run arb detection on merged set
        confirmed_keys = find_arb_keys(merged)
        logger.info("[verify] %d arb(s) confirmed after re-scrape (was %d)", len(confirmed_keys), len(arb_keys))

        async with self._lock:
            self._verified_lines = merged

    def _display_names(self, book_names: set[str]) -> set[str]:
        """Map slug book names → display names for line filtering."""
        return {
            s.display_name
            for s in self._scrapers
            if s.book_name in book_names
        }

    def _get_books_for_keys(
        self,
        lines: list[MarketLine],
        arb_keys: set[tuple[str, str]],
    ) -> set[str]:
        """Return book_name slugs of all books contributing to candidate arb keys."""
        # Build display_name → book_name map
        display_to_slug = {s.display_name: s.book_name for s in self._scrapers}

        books: set[str] = set()
        for line in lines:
            if (line.event_id, line.market) in arb_keys:
                slug = display_to_slug.get(line.book)
                if slug:
                    books.add(slug)
        return books

    async def _scrape_books_by_name(self, book_names: set[str]) -> list[MarketLine]:
        """Concurrently re-scrape the named books; return combined fresh lines."""
        scrapers = [s for s in self._scrapers if s.book_name in book_names]
        results: list[MarketLine] = []

        async def _one(scraper: BookScraper) -> None:
            try:
                lines = await asyncio.to_thread(scraper.scrape_all_sports)
                results.extend(lines)
                logger.info("[verify] %s: %d fresh lines", scraper.book_name, len(lines))
            except Exception as exc:
                logger.error("[verify] Re-scrape failed for %s: %s", scraper.book_name, exc)

        await asyncio.gather(*[_one(s) for s in scrapers], return_exceptions=True)
        return results


# Module-level singleton
scrape_cache = ScrapeCache()
