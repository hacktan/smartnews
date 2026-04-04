# SmartNews — Migration Plan

> **From**: Azure Databricks + Azure Container Apps + Azure OpenAI (`hacktan/SmartNews-Pipeline`)
> **To**: GitHub Actions + DuckDB + Vercel + Render.com (`hacktan/smartnews`)
>
> Created: 2026-04-04
> Status: HISTORICAL PLAN — migration completed; repo now operates on GitHub Actions + DuckDB + Render + Vercel

---

## Strategy

**Do not rewrite from scratch.** The old codebase is mostly reusable:

| What | Reuse | Change needed |
|------|-------|--------------|
| `api/routers/*.py` (14 files) | 100% — copy as-is | Nothing |
| `api/models.py` | 100% — copy as-is | Nothing |
| `api/main.py` | 100% — copy as-is | Nothing |
| `api/db.py` | Replace entirely | Databricks connector → DuckDB |
| `frontend/` (entire) | 100% — copy as-is | Only API URL env var |
| `pipeline/*.py` (was notebooks/) | ~80% | `spark.sql()` → `duckdb.sql()`, Spark MLlib → scikit-learn |
| `.github/workflows/` | Replace entirely | Azure CI/CD → GitHub Actions cron |
| `docs/` | Keep, update | Already carried over |
| `data/` | Keep | Parquet exports reusable as seed data |

---

## What Was Already Done

- [x] New repo created: `hacktan/smartnews` (public)
- [x] Cloned to `c:\Users\haktan\Documents\smartnews`
- [x] Copied from old project:
  - `api/` — all routers, models, db, main
  - `frontend/` — all pages, components, lib
  - `pipeline/` — all 7 scripts (was `notebooks/`)
  - `docs/` — all documentation
  - `data/` — exported parquet + raw RSS
  - `pyproject.toml`, `.gitignore`, `.env.example`, `README.md`

---

## Phase 0 — MCP Setup

> **Goal**: Claude Code connects directly to GitHub and DuckDB. No more manual terminal commands for pipeline management.

- [ ] Create GitHub Personal Access Token (scopes: `repo`, `workflow`, `read:org`)
- [ ] Create `.mcp.json` in project root
- [ ] Install `mcp-server-duckdb` via uv
- [ ] Verify GitHub MCP: Claude can list Actions runs
- [ ] Verify DuckDB MCP: Claude can query local `.duckdb` file

```json
// .mcp.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "<pat>"
      }
    },
    "duckdb": {
      "command": "uv",
      "args": ["run", "mcp-server-duckdb", "--db-path", "./smartnews.duckdb"]
    }
  }
}
```

---

## Phase 1 — DuckDB Pipeline

> **Goal**: All 7 pipeline scripts run locally with DuckDB. No Spark, no Databricks.

### 1A — Dependencies

Update `pyproject.toml`:
- Remove: `pyspark`, `databricks-sdk`, any Azure SDK
- Add: `duckdb`, `scikit-learn` (for KMeans/TF-IDF)
- Keep: `openai`, `trafilatura`, `feedparser`, `httpx`, `fastapi`, `uvicorn`

### 1B — Pipeline Script Conversion

Each script: `spark.sql(...)` → `duckdb.execute(...)` or `duckdb.sql(...)`

Key patterns:

```python
# OLD — Spark session + table read
from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
df = spark.read.table("bronze.raw_feeds")

# NEW — DuckDB connection
import duckdb
conn = duckdb.connect("smartnews.duckdb")
df = conn.execute("SELECT * FROM bronze.raw_feeds").df()
```

```python
# OLD — Spark MLlib clustering
from pyspark.ml.feature import HashingTF, IDF
from pyspark.ml.clustering import KMeans as SparkKMeans

# NEW — scikit-learn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans
```

```python
# OLD — write to Delta table
df.write.mode("overwrite").saveAsTable("serve.article_cards")

# NEW — write to DuckDB
conn.execute("CREATE OR REPLACE TABLE serve.article_cards AS SELECT ...")
```

### 1C — Schema Initialization

Add `pipeline/00_init_schema.py`:
```python
import duckdb
conn = duckdb.connect("smartnews.duckdb")
for schema in ["bronze", "silver", "gold", "serve"]:
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
```

### 1D — Seed Data Import

Import existing parquet exports into DuckDB so pipeline starts with data, not zero:
```python
conn.execute("""
    CREATE TABLE IF NOT EXISTS gold.news_articles AS
    SELECT * FROM read_parquet('data/processed/*.parquet')
""")
```

### 1E — Local Test

```bash
uv run python pipeline/00_init_schema.py
uv run python pipeline/01_bronze_ingestion.py
uv run python pipeline/02_silver_transformation.py
# ... etc
```

---

## Phase 2 — GitHub Actions Pipeline

> **Goal**: Pipeline runs automatically every 4 hours on GitHub's servers. DuckDB file persisted in GitHub Releases.

```yaml
# .github/workflows/pipeline.yml
name: SmartNews Pipeline

on:
  schedule:
    - cron: '0 */4 * * *'
  workflow_dispatch:

jobs:
  pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - run: uv sync

      - name: Download DuckDB from Releases
        run: gh release download latest --pattern "smartnews.duckdb" || echo "Starting fresh"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Run pipeline
        run: |
          uv run python pipeline/00_init_schema.py
          uv run python pipeline/01_bronze_ingestion.py
          uv run python pipeline/01b_fulltext_scraping.py
          uv run python pipeline/02_silver_transformation.py
          uv run python pipeline/03_gold_aggregation.py
          uv run python pipeline/03b_story_matching.py
          uv run python pipeline/04_ai_enrichment.py
          uv run python pipeline/04b_claim_extraction.py
          uv run python pipeline/05_serving_projection.py
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

      - name: Upload DuckDB to Releases
        run: |
          gh release delete latest --yes || true
          gh release create latest smartnews.duckdb \
            --title "Pipeline Run $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
            --notes "Auto-generated"
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Required GitHub Secrets:**
- `OPENAI_API_KEY`

---

## Phase 3 — API Migration

> **Goal**: FastAPI reads from DuckDB instead of Databricks. Deployed on Render.com.

### 3A — Rewrite api/db.py

```python
import duckdb
import httpx
import os

DB_PATH = os.getenv("DUCKDB_PATH", "smartnews.duckdb")
DUCKDB_DOWNLOAD_URL = os.getenv("DUCKDB_DOWNLOAD_URL")  # GitHub Releases URL

def _ensure_db():
    if not os.path.exists(DB_PATH) and DUCKDB_DOWNLOAD_URL:
        r = httpx.get(DUCKDB_DOWNLOAD_URL, follow_redirects=True, timeout=60)
        with open(DB_PATH, "wb") as f:
            f.write(r.content)

_ensure_db()
_conn = duckdb.connect(DB_PATH, read_only=True)

def execute(query: str, params=None):
    return _conn.execute(query, params or []).fetchall()

def fetchdf(query: str, params=None):
    return _conn.execute(query, params or []).df()
```

All router SQL queries remain unchanged.

### 3B — Deploy to Render.com

1. render.com → New Web Service → connect `hacktan/smartnews`
2. Root directory: (root)
3. Build command: `uv sync`
4. Start command: `uv run uvicorn api.main:app --host 0.0.0.0 --port $PORT`
5. Environment variables:
   - `DUCKDB_DOWNLOAD_URL` = GitHub Releases download URL
   - `OPENAI_API_KEY` = OpenAI key

---

## Phase 4 — Frontend Deploy to Vercel

> **Goal**: Next.js on Vercel free tier. Zero config needed — code unchanged.

1. vercel.com → New Project → connect `hacktan/smartnews`
2. Root directory: `frontend/`
3. Framework: Next.js (auto-detected)
4. Environment variable: `NEXT_PUBLIC_API_URL` = Render.com API URL

**Cost: $0**

---

## Phase 5 — Claim Extraction Pipeline

> **Goal**: New pipeline step that extracts verifiable claims from each article.

New file: `pipeline/04b_claim_extraction.py`

- Reads from `gold.news_articles` where `claims_extracted IS NULL` AND `full_text IS NOT NULL`
- Calls GPT-4o-mini to extract atomic factual claims
- Writes to `gold.article_claims (entry_id, claim_text, claim_type, confidence)`
- Marks article as `claims_extracted = TRUE`

---

## Phase 6 — Claims API + Frontend

> **Goal**: Core differentiator goes live. Users can see claim-by-claim cross-source comparison.

### New router: `api/routers/claims.py`
```
GET /api/story/{story_id}/claims
→ Claims grouped by text, with source agreement/dispute breakdown
```

### New frontend page: `frontend/app/story/[id]/page.tsx`
- Story headline + metadata
- All covering sources listed
- Claims section: each claim with color-coded verdict
  - CONSISTENT — all sources agree
  - DISPUTED — sources contradict each other
  - UNVERIFIED — only one source

---

## Old Project Reference

The old project (`hacktan/SmartNews-Pipeline`) remains untouched on Azure.
Credentials and architecture documented in old `docs/AGENT_HANDOFF.md`.
Do not delete old project until Phase 4 is fully live and verified.

---

## Phase Status Tracker

| Phase | Name | Status | Notes |
|-------|------|--------|-------|
| 0 | MCP Setup | ⬜ TODO | |
| 1 | DuckDB Pipeline | ⬜ TODO | |
| 2 | GitHub Actions | ⬜ TODO | |
| 3 | API → Render | ⬜ TODO | |
| 4 | Frontend → Vercel | ⬜ TODO | |
| 5 | Claim Extraction | ⬜ TODO | |
| 6 | Claims API + UI | ⬜ TODO | |
