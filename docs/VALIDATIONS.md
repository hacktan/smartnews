# VALIDATIONS

This file is the operational checklist for validating SmartNews after code or pipeline changes.

## 1) Data Pipeline Validation

Run full pipeline locally in this exact order:

```bash
uv run python pipeline/01_bronze_ingestion.py
uv run python pipeline/01b_fulltext_scraping.py
uv run python pipeline/02_silver_transformation.py
uv run python pipeline/03_gold_aggregation.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/03b_story_matching.py
uv run python pipeline/04b_claim_extraction.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/05_serving_projection.py
uv run python pipeline/validate.py
```

Pass criteria:
- `pipeline/validate.py` exits with code `0`.
- Critical tables are non-empty (`bronze`, `silver`, `gold.news_articles`, `serve.article_cards`).
- Non-critical checks should not regress unexpectedly (`gold.article_claims`, `serve.story_claims`, `serve.compiled_stories`).

### Local LLM mode for claim extraction (RTX 3060 Ti friendly)

Example with Ollama:

```bash
ollama serve
ollama pull qwen2.5:7b-instruct
```

Set env:

```bash
CLAIM_LLM_PROVIDER=local
CLAIM_MODEL=qwen2.5:7b-instruct
LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_OPENAI_API_KEY=ollama
```

Then run only claim step:

```bash
uv run python pipeline/04b_claim_extraction.py
```

Important:
- This local mode is for local runs only.
- GitHub-hosted Actions and remote agents cannot reach your local `127.0.0.1:11434`.
- If CI/remote execution is required, use `OPENAI_API_KEY` or expose a reachable LLM endpoint.

Pass criteria:
- Script runs without `OPENAI_API_KEY`.
- `gold.article_claims` row count increases (if pending matched stories exist).

## 2) API Validation

Minimum smoke checks:

```bash
curl -s https://smartnews-api.onrender.com/health
curl -s https://smartnews-api.onrender.com/api/home
curl -s https://smartnews-api.onrender.com/api/stories?limit=3
curl -s https://smartnews-api.onrender.com/api/story/<story_id>
curl -s https://smartnews-api.onrender.com/api/story/<story_id>/claims
```

Pass criteria:
- `/health` returns `{"status":"ok"}`.
- Story detail returns 200 for a valid `story_id`.
- Story claims endpoint returns 200 and a valid JSON object.

## 3) Frontend Validation

Local:

```bash
cd frontend
npm run build
```

Live smoke checks:

```bash
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/stories
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/story/<story_id>
curl -s -o NUL -w "%{http_code}" https://frontend-chi-brown-98.vercel.app/search?q=ai
```

Pass criteria:
- All routes above return `200`.
- Story page renders claims section when `/api/story/<id>/claims` has data.

## 4) Regression Watchpoints

- Broken article pages (`/article/[id]`) must not return 500.
- Footer GitHub link must point to `https://github.com/hacktan/smartnews`.
- Workflow order in `.github/workflows/pipeline.yml` must include `04b_claim_extraction.py`.

## 5) Latest Validation Loop (2026-04-04)

### Iteration A — Frontend Resilience Pass

Changes applied:
- `frontend/app/sources/page.tsx`
	- Added API error fallback UI.
	- Added empty-state rendering when source leaderboard payload is empty.
- `frontend/app/page.tsx`
	- Hardened narratives extraction with array guards (`Array.isArray`).
- `frontend/app/topic/[name]/page.tsx`
	- Wrapped topic coverage search call with fallback response when API fails.
- `frontend/app/narratives/[arcId]/page.tsx`
	- Added timeline array guard to avoid runtime crashes on malformed/partial payloads.
- `frontend/app/search/page.tsx`
	- Removed unused catch variable found by lint.

Checks run:

```bash
cd frontend
npm run lint
```

Result:
- ESLint completed with no remaining warnings after fixes.

### Iteration B — Live API Smoke

Commands (PowerShell equivalent used):

```bash
GET /health
GET /api/home
GET /api/briefing/daily
GET /api/narratives?limit=5
GET /api/stories?limit=5
GET /api/sources/leaderboard
```

Observed status:
- `200`: `/health`, `/api/home`, `/api/narratives`, `/api/stories`, `/api/sources/leaderboard`
- `404`: `/api/briefing/daily` (no daily briefing row currently available)

Data availability snapshot:
- `/api/narratives?limit=1` currently returns an empty `items` array.
- `/api/stories?limit=1` currently returns an empty `items` array.

Interpretation:
- Blank-route perception is currently dominated by missing upstream data, not only frontend rendering bugs.
- Frontend should continue to prefer explicit empty states over hard failures for all multi-source surfaces.

### Iteration C — Data-State Verification + API Sync Hardening

GitHub trigger attempt:

```bash
gh workflow list
```

Result:
- Blocked by auth in local shell (`HTTP 401: Bad credentials`).

Local pipeline verification command:

```bash
python pipeline/validate.py
```

Result snapshot (local DB):
- `serve.story_arcs: 1`
- `serve.story_claims: 5`
- `serve.daily_briefing: 0`
- All critical checks passed.

Follow-up hardening applied:
- API now syncs `smartnews.duckdb` from GitHub Release on startup by default:
	- `api/config.py` -> `DB_SYNC_ON_STARTUP` (default `true`)
	- `api/main.py` -> startup sync with safe fallback to local DB if sync fails
	- `render.yaml` -> explicit `DB_SYNC_ON_STARTUP="true"`

Operational interpretation:
- Local DB has narrative/claims data, while live API previously returned empty lists for multi-source endpoints.
- Likely cause was stale DB file on running API instance; startup sync + redeploy should close this gap.

### Iteration D — Workflow Recovery Verified (2026-04-04)

Run executed:

```bash
gh run view 23968702286 --json status,conclusion,url
```

Result:
- `status=completed`, `conclusion=success`
- URL: https://github.com/hacktan/smartnews/actions/runs/23968702286

Notable behavior:
- Enrichment-related steps were skipped (expected when provider is `openai` and `OPENAI_API_KEY` is absent).
- Core pipeline, serving projection, validation, and release upload all succeeded.

Post-run live API smoke snapshot:
- `200`: `/health`, `/api/home`, `/api/narratives?limit=3`, `/api/stories?limit=3`, `/api/sources/leaderboard`
- `404`: `/api/briefing/daily`
- counts:
	- `narratives_count=1`
	- `stories_count=0`

Interpretation:
- Pipeline execution path is now stable again.
- Narrative data is now visible live.
- Multi-source compiled stories still require enrichment-capable execution (OpenAI key or reachable local/self-hosted provider).
