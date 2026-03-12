# Arb MVP

Compliance-first arbitrage scanner and stake calculator.

## Architecture

- `backend/`: FastAPI API, source adapters, arbitrage engine
- `frontend/`: React UI for opportunities, stake sizing, and refresh loop

## Why this MVP

- Starts with read-only scanning and stake math.
- Keeps execution manual while you validate latency and account safety.
- Lets you plug in Scrapling and/or an odds API without changing core arb math.

## Quick Start

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend defaults to `http://localhost:8000/api`.

## Next Integrations

1. Replace `MockSource` with live adapters.
2. Implement authenticated `ScraplingSource` sessions per sportsbook.
3. Add line freshness filters and bet-slip confirmation checks.
4. Add optional execution workflows only where terms and regulation allow it.
