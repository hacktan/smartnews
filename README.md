# SmartNews - AI-Enriched Tech News Platform

High-signal, claim-verified tech news platform. Ingests RSS feeds, enriches articles
with AI scores (hype, credibility, importance, freshness), groups related stories across
sources, and serves them through API + web UI.

Tagline: "News that checks its claims"

## Quick Links

- [docs/AGENT_HANDOFF.md](docs/AGENT_HANDOFF.md) - Full project state and runbook
- [docs/README.md](docs/README.md) - Documentation index (active vs archived)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - Technical architecture details
- [docs/PRODUCT_GOALS.md](docs/PRODUCT_GOALS.md) - Product roadmap

## Stack

| Layer | Technology | Status |
|-------|------------|--------|
| Pipeline runner | GitHub Actions cron | Live |
| Database | DuckDB (single file persisted via GitHub Releases) | Live |
| AI enrichment | OpenAI gpt-4o-mini + text-embedding-3-small | Live |
| API | FastAPI + Python 3.11 | Live |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind | Live |
| API hosting | Render.com | Live |
| Frontend hosting | Vercel | Live |

## Data Flow

```text
RSS Feeds
    |
    v
Bronze (raw RSS + full-text scraped)
    |
    v
Silver (cleaned, categorized, word-counted)
    |
    v
Gold (AI-enriched: scores, embeddings, story clusters, claim extraction)
    |
    v
Serve (UI-ready tables: cards, feeds, topics, detail, briefing)
    |
    v
FastAPI  ->  Next.js
```

## Pipeline Run Order

```bash
uv run python pipeline/01_bronze_ingestion.py
uv run python pipeline/01b_fulltext_scraping.py
uv run python pipeline/02_silver_transformation.py
uv run python pipeline/03_gold_aggregation.py
uv run python pipeline/04_ai_enrichment.py      # pass 1: enrich + embeddings
uv run python pipeline/03b_story_matching.py    # needs embeddings
uv run python pipeline/04_ai_enrichment.py      # pass 2: compile stories
uv run python pipeline/05_serving_projection.py
uv run python pipeline/validate.py              # exits 1 on failure
```

Automated via `.github/workflows/pipeline.yml` (every 6 hours).

## Local Setup

```bash
git clone https://github.com/hacktan/smartnews
cd smartnews
cp .env.example .env   # fill OPENAI_API_KEY
uv sync
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| OPENAI_API_KEY | Yes | OpenAI API key |
| DB_PATH | No | DuckDB path (default: smartnews.duckdb) |
| OPENAI_MODEL | No | Chat model (default: gpt-4o-mini) |
| ENRICHMENT_BATCH_LIMIT | No | Max articles per enrichment run (default: 50) |
| GITHUB_TOKEN | API deploy optional | Recommended for private repos or rate-limit safety |
| GITHUB_REPOSITORY | API deploy | Repo slug (default: hacktan/smartnews) |
| GITHUB_RELEASE_TAG | API deploy | Release tag for DB lookup (default: db-latest) |
| GITHUB_DB_ASSET_NAME | API deploy | DB asset filename (default: smartnews.duckdb) |

## API Deploy (Render)

Repository includes `render.yaml` for one-click Blueprint deploy.

Manual equivalent:

```bash
pip install uv && uv sync --project api
uv run --project api uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
