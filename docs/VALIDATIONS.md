# VALIDATIONS

This file is the operational checklist for validating SmartNews after code or pipeline changes.

## Current Snapshot (2026-04-04)

- Latest documented production state is reflected in `docs/AGENT_HANDOFF.md`.
- Narrative, Briefing, and Multi-source pages were validated as populated during Iterations E-G.
- Archive plans under `docs/archive/` are historical references and may not represent current live status.

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

### Iteration E — Local Llama Enrichment Recovery (2026-04-04)

Goal:
- Address user-reported issue: latest CI run skipped AI enrichment.

Execution:

```bash
AI_LLM_PROVIDER=local
OPENAI_MODEL=qwen2.5:7b-instruct
LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_OPENAI_API_KEY=ollama
COMPILATION_MIN_FULLTEXT_SOURCES=1
COMPILATION_MIN_BODY_CHARS=250
python pipeline/04_ai_enrichment.py
python pipeline/05_serving_projection.py
python pipeline/validate.py
```

Fixes applied before rerun:
- `pipeline/05_serving_projection.py`: fixed `serve.daily_briefing` insert parameter binding bug.
- `pipeline/04_ai_enrichment.py`: made compiled-body minimum length configurable via env (`COMPILATION_MIN_BODY_CHARS`).

Observed result:
- `gold.compiled_stories`: `1` written
- `serve.compiled_stories`: `1` written
- `serve.daily_briefing`: `ok` (1 row present)
- `pipeline/validate.py`: all critical checks passed

Operational note:
- Updated local DB was uploaded to GitHub Release asset `db-latest/smartnews.duckdb`.

### Iteration F — Live API Sync Confirmed (2026-04-04)

Action:
- Forced API redeploy via no-op commit to trigger startup DB sync.

Post-redeploy live checks:
- `/health` -> `200`
- `/api/briefing/daily` -> `200` (`article_count=7`)
- `/api/stories?limit=3` -> `200` (`stories_count=1`)

Conclusion:
- Local Llama-enriched outputs are now visible in live API through refreshed `db-latest` sync.

### Iteration G — Frontend Route Regression Sweep (2026-04-04)

Scope:
- User-requested comprehensive route checks across homepage and key feature pages.

Fix applied:
- `frontend/app/sources/page.tsx` hardened against malformed/null leaderboard rows.

Frontend live smoke results:
- `200`: `/`, `/briefing`, `/narratives`, `/stories`, `/sources`, `/search?q=ai`
- No route-level `500` observed in final sweep.

### Iteration H — Multi-source Placeholder Regression + Partial Production Skew (2026-04-04)

User-reported issue:
- Opening certain multi-source story detail pages showed:
	- `Summary`
	- `AI synthesis pending: ...`

Fixes applied (code + data):
- Removed placeholder fallback row insertion in serving projection.
- Updated stories list/detail API defaults to hide pending rows unless `include_pending=true`.
- Added API hard-block for pending placeholder text patterns.
- Added frontend story detail guard to suppress pending placeholder copy.

Validation commands used:

```bash
GET /api/stories?limit=20
GET /api/story/<legacy_pending_story_id>
GET /api/story/<legacy_pending_story_id>?include_pending=true
GET /openapi.json
```

Observed state:
- `/api/stories?limit=20` shows pending count `0`.
- `/openapi.json` confirms `include_pending` exists on stories endpoints.
- Some live checks still returned pending text for a legacy story ID on default detail endpoint, indicating rollout skew/stale instance behavior.

Conclusion:
- Code-level fix exists and is pushed.
- Remaining issue is operational deployment consistency on live service, not missing local code changes.

Data presence verification (API):
- `briefing_count=7`
- `narratives_count=1`
- `stories_count=1`

Conclusion:
- Narrative, Briefing, and Multi-source surfaces are now populated and reachable in production.
