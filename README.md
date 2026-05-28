# Wabash — Product Match POC

Find and score product detail page (PDP) matches for a manufacturer name + MPN using SerpAPI, Firecrawl, and LLM-assisted similarity scoring.

Adapted from the PDP Testing Lab stack (FastAPI + React/Vite) at `Lab/pdp-testing-lab`.

## Workflow

1. **Search** — SerpAPI (Google US/en) with query variants; rank top 1–5 candidates; filter listing/search pages.
2. **Scrape** — Firecrawl `onlyMainContent` markdown per candidate; skip oversized/untrusted PDFs.
3. **Score** — LLM returns per-criterion 0–100% scores and an overall similarity % per source.

## Prerequisites

- Python 3.11+
- Node.js 18+
- API keys: `SERPAPI_API_KEY`, `FIRECRAWL_API_KEY`, and at least one LLM provider (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `XAI_API_KEY`)

## Setup

### Backend

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys

python -m venv .venv
source .venv/bin/activate
pip install -e .

python -m app.run
# Listens on http://127.0.0.1:8001
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# http://localhost:5173 — proxies /api → backend
```

Optional: set `AUTH_PASSWORD` in `backend/.env` to require login (same cookie session pattern as PDP Lab).

## Example API call

```bash
curl -s -X POST http://127.0.0.1:8001/match/run \
  -H "Content-Type: application/json" \
  -d '{"manufacturer_name":"WHITING DOOR","manufacturer_product_number":"ML5035"}' | jq .
```

## Manual test case

| Manufacturer   | MPN    |
|----------------|--------|
| WHITING DOOR   | ML5035 |

Also try products listed on [onewabash.com/products](https://onewabash.com/products) — `onewabash.com` is in the authorized distributor allowlist.

## Environment variables

See [backend/.env.example](backend/.env.example). Key settings:

| Variable | Purpose |
|----------|---------|
| `WABASH_MATCH_MODEL` | LLM for scoring (default `gpt-4o-mini`) |
| `RESEARCH_CANDIDATE_LIMIT` | Max Serp candidates (default 5) |
| `RESEARCH_PDF_MAX_BYTES` | Skip large PDFs |
| `SERPAPI` / `FIRECRAWL` / `AUTH_*` | Same family as PDP Lab |

## Project layout

```
Wabash/
├── backend/app/research/   # searcher, ranker, scorer, matcher
├── backend/app/api/      # auth, match
└── frontend/src/         # Match UI
```
