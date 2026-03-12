import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# Suppress scrapling's deprecated-API warnings (internal library noise)
logging.getLogger("scrapling").setLevel(logging.ERROR)

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.auth import require_api_key
from app.services.opportunity_service import OpportunityService
from app.services.scrape_cache import BookStatus, scrape_cache
from app.sources.api_source import OddsApiSource
from app.sources.base import OddsSourceAdapter
from app.sources.mock_source import MockSource
from app.sources.scrapling_source import ScraplingSource


def build_scrapers():
    """Instantiate book scrapers based on config credentials."""
    scrapers = []

    try:
        from app.scrapers.draftkings import DraftKingsScraper
        from app.scrapers.fanduel import FanDuelScraper
        from app.scrapers.betrivers import BetRiversScraper
        from app.scrapers.betmgm import BetMGMScraper

        scrapers.append(DraftKingsScraper(settings.draftkings_email, settings.draftkings_password))
        scrapers.append(FanDuelScraper(settings.fanduel_email, settings.fanduel_password))
        scrapers.append(BetRiversScraper("", "", state=settings.betrivers_state))
        scrapers.append(BetMGMScraper("", ""))
    except ImportError:
        pass  # scrapling[playwright] not installed; scrapers unavailable

    return scrapers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    if settings.enable_scrapling_source:
        scrapers = build_scrapers()
        scrape_cache._playwright_interval = settings.playwright_interval_seconds
        scrape_cache._api_interval = settings.api_interval_seconds
        scrape_cache.start(scrapers)

    yield

    scrape_cache.stop()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
    dependencies=[Depends(require_api_key)],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def build_sources() -> list[OddsSourceAdapter]:
    sources: list[OddsSourceAdapter] = []

    if settings.enable_mock_source:
        sources.append(MockSource())

    if settings.enable_odds_api_source:
        sources.append(OddsApiSource(api_key=settings.odds_api_key, sport_key=settings.odds_api_sport))

    if settings.enable_scrapling_source:
        sources.append(ScraplingSource(books=settings.scrapling_book_list))

    return sources


@app.get("/health", dependencies=[])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get(f"{settings.api_prefix}/sources")
def get_sources() -> dict[str, list[str]]:
    return {"sources": [source.source_name for source in build_sources()]}


@app.get(f"{settings.api_prefix}/opportunities")
async def get_opportunities(total_stake: float = Query(default=100.0, gt=0.0)) -> dict[str, object]:
    service = OpportunityService(build_sources())
    opportunities = await service.find_opportunities(total_stake=total_stake)

    return {
        "count": len(opportunities),
        "opportunities": [opportunity.model_dump() for opportunity in opportunities],
    }


@app.get(f"{settings.api_prefix}/books/status")
async def get_book_status() -> dict[str, object]:
    status_map = await scrape_cache.get_status()
    return {
        "books": {
            name: {
                "book": s.book,
                "display_name": s.display_name,
                "logged_in": s.logged_in,
                "last_scraped_at": s.last_scraped_at.isoformat() if s.last_scraped_at else None,
                "last_error": s.last_error,
                "line_count": s.line_count,
                "sport_counts": s.sport_counts,
            }
            for name, s in status_map.items()
        }
    }


@app.get(f"{settings.api_prefix}/debug/lines")
async def debug_lines() -> dict[str, object]:
    from collections import defaultdict
    all_lines = await scrape_cache.get_all_lines()
    verified_lines = await scrape_cache.get_lines()
    grouped: dict = defaultdict(list)
    for l in all_lines:
        grouped[(l.event_id, l.market)].append({"book": l.book, "outcome": l.outcome, "odds": l.american_odds})
    cross_book = {f"{eid}|{mkt}": v for (eid, mkt), v in grouped.items() if len(set(x["book"] for x in v)) > 1}
    by_book = defaultdict(int)
    for l in all_lines:
        by_book[l.book] += 1
    return {
        "total_lines": len(all_lines),
        "verified_lines": len(verified_lines),
        "by_book": dict(by_book),
        "cross_book_count": len(cross_book),
        "cross_book_sample": dict(list(cross_book.items())[:10]),
    }


@app.post(f"{settings.api_prefix}/books/{{book}}/refresh")
async def refresh_book(book: str) -> dict[str, str]:
    status_map = await scrape_cache.get_status()
    if book not in status_map:
        raise HTTPException(status_code=404, detail=f"Book '{book}' not found or not configured")

    import asyncio
    asyncio.create_task(scrape_cache.refresh_book(book))
    return {"status": "refresh triggered", "book": book}
