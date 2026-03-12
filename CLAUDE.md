# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Backend
```bash
# Run dev server (from repo root or backend/)
cd backend && .venv/Scripts/uvicorn app.main:app --reload --port 8000

# Run tests
cd backend && python -m pytest tests/ -v

# Run a single test
cd backend && python -m pytest tests/test_engine.py::test_function_name -v

# Install dependencies (no venv; user uses global pip)
pip install --user -e backend/
pip install --user "scrapling[playwright]"  # for live scraping
```

### Frontend
```bash
cd frontend && npm install
cd frontend && npm run dev        # Vite dev server on :5173
cd frontend && npm run build      # tsc -b && vite build → dist/
```

## Architecture

### Data Flow
1. At startup, `ScrapeCache.start(scrapers)` launches a background loop (default 60s interval) that runs each book scraper in `asyncio.to_thread()`.
2. `ScraplingSource.fetch_lines()` reads from the in-memory cache instantly (no blocking).
3. `/api/opportunities` calls `find_arbitrage_opportunities(lines, total_stake)` against the cached data.
4. The frontend polls `/api/opportunities` and `/api/books/status` every 10s.

### Source Adapters (`app/sources/`)
Three interchangeable adapters implement `OddsSourceAdapter`:
- **MockSource** — static test data, no network
- **OddsApiSource** — third-party OddsAPI.io REST API
- **ScraplingSource** — reads from `ScrapeCache` (live book scrapers)

Active adapters are controlled by `.env` flags: `ENABLE_MOCK_SOURCE`, `ENABLE_ODDS_API_SOURCE`, `ENABLE_SCRAPLING_SOURCE`.

### Book Scrapers (`app/scrapers/`)
- **DraftKings / FanDuel / BetMGM** — Playwright-based, parse DOM via aria-labels or Angular `ms-event` elements
- **BetRivers / BallyBet / betPARX** — Kambi JSON API (no login), state-specific via `BETRIVERS_STATE` / `BALLYBET_STATE` / `BETPARX_STATE` env vars

### Auth
`require_api_key` FastAPI dependency is applied to all `/api/*` routes. Auth is disabled when `API_KEY=""` in `.env`. `/health` is always open.

### Key Models
- `MarketLine` (`app/models/odds.py`) — one odds line from one book
- `ArbitrageOpportunity` (`app/models/opportunity.py`) — profitable multi-leg opportunity with stake breakdown

## Configuration
Copy `backend/.env.example` → `backend/.env` and `frontend/.env.example` → `frontend/.env`.

Key backend env vars:
- `ENABLE_SCRAPLING_SOURCE=true` — enables live scraping
- `SCRAPLING_BOOKS` — comma-separated list of active scrapers
- `SPORTS` — comma-separated: `nfl,nba,mlb,nhl,soccer`
- `SCRAPE_INTERVAL_SECONDS` — default 60
- `API_KEY` — leave empty to disable auth

## Notes
- `backend/sessions/` is gitignored; it holds Playwright browser profiles/cookies for stateful scrapers
- FanDuel may trigger SMS 2FA on first login
- `scrapling[playwright]` extra must be installed for live scraping to work
