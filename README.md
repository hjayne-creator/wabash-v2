# Wabash V2 — Attribute Research

Research commercial transportation part attributes from the web (Perplexity Agent or Parallel Task API), map results to an admin-managed attribute catalog, and report fill rate and cost per run.

## Workflow

1. **Research** — User enters manufacturer + MPN and selects a web-research engine.
2. **Extract** — Engine returns structured JSON attributes and sources.
3. **Match** — Deterministic matcher maps LLM keys to catalog attributes (exact → alias → fuzzy).
4. **Report** — Each run is persisted with fill %, cost, and full output.

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys:
  - `PERPLEXITY_API_KEY` (default engine)
  - `PARALLEL_API_KEY` (optional alternate engine — Parallel Task API)
  - `OPENAI_API_KEY` (optional; used by workflow helpers, not the Parallel engine)

## Setup

### Backend

```bash
cd backend
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m app.run
```

Backend: http://127.0.0.1:8001

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173 (proxies `/api` to backend)

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/research/run` | Run attribute research |
| GET | `/research/engines` | List engines |
| GET | `/research/runs` | List persisted runs |
| GET | `/research/runs/{id}` | Run detail |
| GET/POST/PATCH/DELETE | `/admin/attributes` | Attribute catalog CRUD |
