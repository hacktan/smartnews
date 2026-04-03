# SmartNews — Agent Handoff & Complete Project State

> **PURPOSE**: Single source of truth for any AI agent, developer, or new team member.
> Read this **entire** document before touching any code.
>
> **Last updated**: 2026-04-04 — Phases 0, 1, 2 complete. Phase 3 code complete (deploy pending).
>
> **Repo**: `hacktan/smartnews` — local path: `c:\Users\haktan\Documents\SmartNews`
> **Old repo (DO NOT run, DO NOT delete)**: `hacktan/SmartNews-Pipeline` (Azure/Databricks)

---

## 1. What Is This Project?

**SmartNews** is a high-signal, claim-verified news discovery platform. It ingests RSS
articles, runs them through a Medallion pipeline (Bronze → Silver → Gold → Serve),
enriches them with AI scores (hype, credibility, importance, freshness), cross-matches
stories across sources using embedding cosine similarity, and serves them through a
structured web UI.

**Core differentiator**: cross-source claim verification — surface where sources agree,
where they disagree, and what's missing.

**Tagline**: "News that checks its claims"

---

## 2. Migration Status

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | MCP Setup | ✅ DONE | `.mcp.json` with GitHub + DuckDB MCP servers |
| 1 | DuckDB pipeline conversion | ✅ DONE | All 7 pipeline scripts: Spark → DuckDB + scikit-learn |
| 2 | GitHub Actions cron | ✅ DONE | `.github/workflows/pipeline.yml`, db-latest release pattern |
| **3** | **API db.py rewrite + Render.com** | **🟨 IN PROGRESS — CODE DONE** | Render deploy pending |
| 4 | Frontend → Vercel | ⬜ TODO | Only API URL env var changes |
| 5 | Claim extraction pipeline | ⬜ TODO | `pipeline/04b_claim_extraction.py` (new file) |
| 6 | Claims API + frontend `/story/[id]` | ⬜ TODO | Depends on Phase 5 |

---

## 3. Stack

| Layer | Technology | Status |
|-------|-----------|--------|
| Pipeline runner | GitHub Actions cron (every 6h) | ✅ Live |
| Database | DuckDB single file `smartnews.duckdb` | ✅ Schema defined |
| DB persistence | GitHub Releases `db-latest` tag | ✅ Workflow configured |
| AI enrichment | OpenAI `gpt-4o-mini` | ✅ In pipeline |
| Embeddings | OpenAI `text-embedding-3-small` | ✅ In pipeline |
| Clustering | scikit-learn KMeans | ✅ In pipeline/05 |
| API | FastAPI + Python 3.11 | ✅ Migrated to DuckDB |
| API hosting | Render.com | 🟨 Deploy pending |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind | ⚠ Code ready, not yet deployed (Phase 4) |
| Frontend hosting | Vercel | ⬜ Phase 4 |
| Dev tools | Claude Code + MCP (GitHub + DuckDB) | ✅ `.mcp.json` configured |

---

## 4. Directory Structure

```
SmartNews/
├── .github/
│   └── workflows/
│       └── pipeline.yml       # Cron + DB upload/download (Phase 2)
├── pipeline/                  # Data pipeline (run in exact order, see §6)
│   ├── 01_bronze_ingestion.py
│   ├── 01b_fulltext_scraping.py
│   ├── 02_silver_transformation.py
│   ├── 03_gold_aggregation.py
│   ├── 03b_story_matching.py
│   ├── 04_ai_enrichment.py
│   ├── 05_serving_projection.py
│   └── validate.py            # Post-run validation, exits 1 on failure
├── api/                       # FastAPI app (Phase 3 code complete)
│   ├── db.py                  # DuckDB read-only connector
│   ├── config.py              # API settings (+ GitHub release download vars)
│   ├── main.py                # startup DB download + app lifecycle
│   ├── models.py              # Pydantic response models
│   ├── routers/               # 14 files, all reading from `serve.*`
│   └── pyproject.toml         # DuckDB-based API dependencies
├── frontend/                  # Next.js app (DO NOT touch until Phase 4)
├── docs/                      # Documentation (this file)
├── pyproject.toml             # Pipeline deps (duckdb, openai, trafilatura, sklearn…)
├── .env.example               # Template — copy to .env
├── .gitignore                 # smartnews.duckdb + .env + .mcp.json gitignored
└── smartnews.duckdb           # GITIGNORED — persisted via GitHub Releases db-latest
```

---

## 5. DuckDB Schema

Single file `smartnews.duckdb`, organized in schemas:

### bronze
| Table | PK | Description |
|-------|-----|-------------|
| `bronze.rss_raw` | `entry_id` (md5 of URL/id) | Raw RSS entries |
| `bronze.article_fulltext` | `entry_id` | Scraped full text + og:image (trafilatura) |

### silver
| Table | PK | Description |
|-------|-----|-------------|
| `silver.rss_cleaned` | `entry_id` | Cleaned, categorized, word-counted |

### gold
| Table | PK | Description |
|-------|-----|-------------|
| `gold.news_articles` | `entry_id` | All-time articles + AI enrichment cols (`enriched_at IS NULL` = pending) |
| `gold.daily_category_summary` | `(report_date, category)` | Daily category aggregation |
| `gold.daily_source_summary` | `(report_date, feed_source)` | Daily source aggregation |
| `gold.story_matches` | `story_id` | Cross-source story groups |
| `gold.compiled_stories` | `story_id` | AI-synthesized multi-source articles |

### serve (API reads ONLY from these — never from gold directly)
| Table | PK | Description |
|-------|-----|-------------|
| `serve.article_cards` | `entry_id` | Flat card objects for browsing/homepage |
| `serve.category_feeds` | `(entry_id, category)` | Per-category feeds |
| `serve.trending_topics` | `topic` | Topic aggregations for trending section |
| `serve.article_detail` | `entry_id` | Full enriched objects for `/article/[id]` |
| `serve.story_clusters` | `cluster_id` | KMeans clusters for cluster section |
| `serve.entity_index` | `(entity_name, entry_id)` | Entity → article mappings |
| `serve.daily_briefing` | `briefing_date` | AI-generated 5-bullet daily briefing |
| `serve.hype_snapshots` | `(topic, snapshot_date)` | Daily score snapshots (trend tracking) |
| `serve.story_arcs` | `arc_id` | Narrative arcs grouped by subtopic |
| `serve.compiled_stories` | `story_id` | Compiled multi-source stories |

---

## 6. Pipeline Execution Order (CRITICAL)

```
01_bronze_ingestion      → RSS feeds → bronze.rss_raw
01b_fulltext_scraping    → URLs → bronze.article_fulltext   (continue-on-error)
02_silver_transformation → clean/categorize → silver.rss_cleaned
03_gold_aggregation      → aggregate → gold.news_articles + gold.daily_*
04_ai_enrichment (pass1) → OpenAI → gold.news_articles [enriched_at, embedding]
03b_story_matching       → uses embeddings → gold.story_matches
04_ai_enrichment (pass2) → skips enrichment (done), compiles → gold.compiled_stories
05_serving_projection    → rebuilds all serve.* tables
validate                 → checks row counts, exits 1 on failure
```

**Why 04 runs twice**: Pass 1 enriches articles + generates embeddings. Story matching (03b)
needs those embeddings. Pass 2 is cheap — `enriched_at IS NOT NULL` guard skips re-enrichment,
only story compilation runs.

### Local run
```bash
cd c:\Users\haktan\Documents\SmartNews
cp .env.example .env          # fill in OPENAI_API_KEY
uv sync
uv run python pipeline/01_bronze_ingestion.py
uv run python pipeline/01b_fulltext_scraping.py
uv run python pipeline/02_silver_transformation.py
uv run python pipeline/03_gold_aggregation.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/03b_story_matching.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/05_serving_projection.py
uv run python pipeline/validate.py
```

---

## 7. Environment Variables

### Pipeline
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | **YES** | — | OpenAI API key |
| `DB_PATH` | no | `smartnews.duckdb` (project root) | DuckDB file path |
| `OPENAI_MODEL` | no | `gpt-4o-mini` | Chat model |
| `OPENAI_EMBEDDING_MODEL` | no | `text-embedding-3-small` | Embedding model |
| `ENRICHMENT_BATCH_LIMIT` | no | `50` | Max articles per enrichment run |
| `SCRAPE_BATCH_LIMIT` | no | `100` | Max articles per scraping run |

### API (Phase 3 — after rewrite)
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DB_PATH` | **YES** | — | Path to DuckDB file (downloaded at startup) |
| `GITHUB_TOKEN` | no (recommended) | — | Needed for private repos or to avoid GitHub rate limits |
| `GITHUB_REPOSITORY` | no | `hacktan/smartnews` | Repository slug for release lookup |
| `GITHUB_RELEASE_TAG` | no | `db-latest` | Release tag containing DB asset |
| `GITHUB_DB_ASSET_NAME` | no | `smartnews.duckdb` | Asset filename to download |
| `CORS_ORIGINS` | no | `*` | Comma-separated allowed origins |
| `CACHE_TTL_SECONDS` | no | `180` | TTL cache for API responses |
| `HOME_TOP_STORIES_LIMIT` | no | `10` | Homepage article count |
| `CATEGORY_PAGE_SIZE` | no | `20` | Articles per category page |
| `SEARCH_MAX_RESULTS` | no | `30` | Max search results |

### GitHub Actions secrets (repo Settings → Secrets → Actions)
| Secret | Description |
|--------|-------------|
| `OPENAI_API_KEY` | OpenAI API key |

`GITHUB_TOKEN` is optional for public repos; recommended in production to avoid rate limits.

---

## 8. GitHub Actions Workflow

File: `.github/workflows/pipeline.yml`

- **Trigger**: Every 6 hours (`0 */6 * * *`) + `workflow_dispatch` (manual)
- **Manual inputs**: `skip_scraping` (bool), `skip_enrichment` (bool)
- **Concurrency**: `group: pipeline` — only one run at a time, never cancel mid-run
- **DB pattern**:
  1. `gh release view db-latest` — create release on first run only
  2. `gh release download db-latest --pattern "smartnews.duckdb"` — get existing DB
  3. Run pipeline steps
  4. `uv run python pipeline/validate.py` — fails job if serve tables are empty
  5. `gh release upload db-latest smartnews.duckdb --clobber` — only if success

---

## 9. API Architecture (Current State)

The API is a FastAPI app with 14 routers. All routers follow the same pattern:

```python
from ..db import query
rows = query("SELECT ... FROM serve.article_cards WHERE ...", (param,))
```

The `db.query()` interface remained stable during migration. All 14 routers use `?`
for params (same as DuckDB).

**Current `api/db.py`**: DuckDB read-only connection to `smartnews.duckdb`.
**Startup behavior**: if DB is missing, download `smartnews.duckdb` from GitHub Releases.

---

## 10. Phase 3 — Exact Steps (API Rewrite + Render.com)

Status: code migration is complete in this repository. Keep this section as implementation reference.

### Step 1: Update `api/pyproject.toml`

Remove `databricks-sql-connector>=3.4.0`, add `duckdb>=0.10`.

### Step 2: Rewrite `api/db.py`

Replace entirely with:

```python
"""
DuckDB connection for SmartNews API.
Connects read-only to smartnews.duckdb.
DB_PATH must be set and the file must exist before starting the server.
"""
import logging
import os
from typing import Any

import duckdb

logger = logging.getLogger(__name__)

DB_PATH = os.getenv("DB_PATH", "smartnews.duckdb")

_connection: duckdb.DuckDBPyConnection | None = None


def get_connection() -> duckdb.DuckDBPyConnection:
    global _connection
    if _connection is None:
        _connection = duckdb.connect(DB_PATH, read_only=True)
        logger.info("DuckDB connection opened: %s", DB_PATH)
    return _connection


def close_connection() -> None:
    global _connection
    if _connection is not None:
        _connection.close()
        _connection = None
        logger.info("DuckDB connection closed.")


def _run_query(sql: str, params: tuple) -> list[dict[str, Any]]:
    con = get_connection()
    result = con.execute(sql, list(params))
    if result.description is None:
        return []
    columns = [col[0] for col in result.description]
    return [dict(zip(columns, row)) for row in result.fetchall()]


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Execute a SELECT query and return results as list of dicts."""
    try:
        return _run_query(sql, params)
    except Exception as first_err:
        logger.warning("Query failed (%s), reconnecting once...", first_err)
        close_connection()
        return _run_query(sql, params)


def execute(sql: str, params: tuple = ()) -> None:
    """Execute a write statement. (API is read-only — this is a no-op guard.)"""
    raise RuntimeError("API is read-only. Use pipeline scripts to write data.")
```

### Step 3: Rewrite `api/config.py`

Remove all Databricks/Azure settings. New version:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # DuckDB
    db_path: str = "smartnews.duckdb"

    # App
    cors_origins: str = "*"
    cache_ttl_seconds: int = 180
    home_top_stories_limit: int = 10
    category_page_size: int = 20
    search_max_results: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


settings = Settings()
```

### Step 4: Fix SQL prefix in all 12 router files

**This is a pure string replacement** — no logic changes.

Replace every occurrence of `dbc_mcp_projects.serve.` with `serve.` in these files:
```
api/routers/articles.py    (2 occurrences)
api/routers/briefing.py    (1 occurrence)
api/routers/categories.py  (3 occurrences)
api/routers/clusters.py    (4 occurrences)
api/routers/entities.py    (3 occurrences)
api/routers/home.py        (6 occurrences)
api/routers/insights.py    (2 occurrences)
api/routers/narratives.py  (3 occurrences)
api/routers/search.py      (2 occurrences)
api/routers/sources.py     (1 occurrence)
api/routers/stories.py     (3 occurrences)
api/routers/topics.py      (1 occurrence)
```

Shell command to do all at once:
```bash
# In c:\Users\haktan\Documents\SmartNews
find api/routers -name "*.py" -exec sed -i 's/dbc_mcp_projects\.serve\./serve\./g' {} +
```

Or use Claude Code Edit tool file by file with `replace_all: true`.

### Step 5: Update `api/main.py`

Update the lifespan to download DB at startup and fix docstring.
Implementation now uses GitHub REST API (no `gh` CLI dependency):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(settings.db_path):
        logger.info("Downloading database from GitHub Releases...")
        _download_db_from_github(settings.db_path)
        logger.info("Database downloaded: %s", settings.db_path)
    logger.info("SmartNews API starting up.")
    yield
    logger.info("SmartNews API shutting down.")
    close_connection()
```

Also update the FastAPI description string (remove Databricks references).

### Step 6: Deploy to Render.com

1. Go to render.com → New → Web Service → connect `hacktan/smartnews`
2. Settings:
   - **Root directory**: repository root
   - **Build command**: `pip install uv && uv sync --project api`
   - **Start command**: `uv run --project api uvicorn api.main:app --host 0.0.0.0 --port $PORT`
   - **Environment**: Python 3.11
3. Environment variables (in Render dashboard):
   - `DB_PATH` = `smartnews.duckdb`
   - `GITHUB_TOKEN` = optional but recommended (PAT with `repo` read scope)
   - `GITHUB_REPOSITORY` = `hacktan/smartnews` (optional)
   - `GITHUB_RELEASE_TAG` = `db-latest` (optional)
   - `GITHUB_DB_ASSET_NAME` = `smartnews.duckdb` (optional)
   - `CORS_ORIGINS` = `*` (update after frontend deployed)
4. Test: `GET https://your-app.onrender.com/health` should return `{"status": "ok"}`

---

## 11. Phase 4 Preview (Frontend → Vercel)

File to change: `frontend/.env.local` (create it):
```
NEXT_PUBLIC_API_URL=https://your-smartnews-api.onrender.com
```

Reference template is available at `frontend/.env.local.example`.

That's it. No code changes to frontend needed.

Deploy: Vercel dashboard → Import `hacktan/smartnews` → Framework: Next.js → Root dir: `frontend` → Add env var above.

---

## 12. Scoring System (UI Contract)

Scores are signals, not verdicts. **UI must use soft labels** — never "good" or "bad":

| Score | Soft label range |
|-------|-----------------|
| `hype_score` | "Measured" ↔ "Attention-grabbing" |
| `credibility_score` | "Unverified" ↔ "Well-sourced" |
| `importance_score` | "Background" ↔ "Breaking" |
| `freshness_score` | Exponential decay, half-life 3 days |

---

## 13. Rules (Non-Negotiable)

- **Never run the Databricks pipeline** — `hacktan/SmartNews-Pipeline` costs money
- **Never commit `smartnews.duckdb`** — gitignored, lives in GitHub Releases
- **Never commit `.env` or `.mcp.json`** — contain secrets
- **Always `uv run python`** (not bare `python`) on Windows
- **No Co-Authored-By in commits** — user wants sole authorship
- **All code/docs in English** — conversations in Turkish
- **API data flow**: `serve.* → API → frontend` — never read from `gold.*` in API
- **Scores are signals** — UI must use soft labels, never hard "bad/good" judgments

---

## 14. Key Files Quick Reference

| Need to... | File |
|-----------|------|
| Understand full architecture | `docs/ARCHITECTURE.md` |
| See Phase 3 exact changes | This doc §10 |
| Run pipeline locally | `docs/AGENT_HANDOFF.md` §6 |
| Add new RSS feeds | `pipeline/01_bronze_ingestion.py` → `RSS_FEEDS` list |
| Change AI prompt | `pipeline/04_ai_enrichment.py` → `SYSTEM_PROMPT` |
| Change serve table logic | `pipeline/05_serving_projection.py` |
| Validate pipeline output | `uv run python pipeline/validate.py` |
| Check GitHub Actions | `.github/workflows/pipeline.yml` |
