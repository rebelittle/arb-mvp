"""Base class for all book scrapers."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path

from app.models.odds import MarketLine

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path(__file__).parent.parent.parent / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

# Per-book persistent browser profile directories (improves anti-bot bypass)
BROWSER_PROFILES_DIR = SESSIONS_DIR / "browser_profiles"
BROWSER_PROFILES_DIR.mkdir(exist_ok=True)


class SessionExpiredError(Exception):
    """Raised when the scraper detects the session is no longer valid."""


class BookScraper(ABC):
    book_name: str       # e.g. "draftkings"
    display_name: str    # e.g. "DraftKings"
    SPORT_URLS: dict[str, str]  # sport_key → full URL
    scrape_type: str = "playwright"  # "playwright" | "api"

    def __init__(self, email: str, password: str) -> None:
        self.email = email
        self.password = password
        self._session_file = SESSIONS_DIR / f"{self.book_name}.json"
        self._browser_profile = str(BROWSER_PROFILES_DIR / self.book_name)

    # ------------------------------------------------------------------ #
    # Abstract interface                                                   #
    # ------------------------------------------------------------------ #

    @abstractmethod
    def login(self, page_action_fn) -> None:
        """Return a page_action callable for use with DynamicFetcher.fetch()."""

    @abstractmethod
    def parse_lines(self, page: object, sport: str) -> list[MarketLine]:
        """Parse odds lines from a fetched Response for the given sport."""

    # ------------------------------------------------------------------ #
    # Session helpers                                                      #
    # ------------------------------------------------------------------ #

    def _load_cookies(self) -> list[dict] | None:
        if self._session_file.exists():
            try:
                data = json.loads(self._session_file.read_text(encoding="utf-8"))
                return data.get("cookies")
            except Exception:
                return None
        return None

    def _save_cookies(self, cookies: list[dict]) -> None:
        try:
            self._session_file.write_text(
                json.dumps({"cookies": cookies}, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("[%s] Could not save session: %s", self.book_name, exc)

    def is_login_redirect(self, url: str) -> bool:
        indicators = ["/login", "sign-in", "signin", "/auth"]
        url_lower = url.lower()
        return any(ind in url_lower for ind in indicators)

    def login_and_save_session(self) -> None:
        """Not yet implemented — placeholder for future credential-based login."""
        raise NotImplementedError("Credential login not yet implemented")

    # ------------------------------------------------------------------ #
    # Main entry point                                                     #
    # ------------------------------------------------------------------ #

    def scrape_all_sports(self) -> list[MarketLine]:
        """Scrape all configured sports. Returns a flat list of MarketLine objects."""
        try:
            from scrapling.fetchers import DynamicFetcher  # type: ignore
        except Exception as exc:
            raise RuntimeError(f"scrapling import failed: {exc}") from exc

        cookies = self._load_cookies() or []

        all_lines: list[MarketLine] = []
        for sport, url in self.SPORT_URLS.items():
            try:
                page = DynamicFetcher().fetch(
                    url,
                    headless=True,
                    network_idle=True,
                    timeout=60000,
                    cookies=cookies,
                )
                if page.status in (403, 429, 503):
                    raise RuntimeError(
                        f"HTTP {page.status} — blocked by anti-bot on {sport}"
                    )
                if self.is_login_redirect(page.url):
                    raise SessionExpiredError(
                        f"[{self.book_name}] Redirected to login on {sport}"
                    )
                lines = self.parse_lines(page, sport)
                all_lines.extend(lines)
                logger.info("[%s] %s: %d lines", self.book_name, sport, len(lines))
            except SessionExpiredError:
                raise
            except Exception as exc:
                logger.error("[%s] Error scraping %s: %s", self.book_name, sport, exc)

        return all_lines
