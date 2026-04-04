# SmartNews - Agent Handoff

> Canonical handoff doc for the next agent.
> Last updated: 2026-04-04 (post Iteration H)
> Repo: hacktan/smartnews
> Local path: c:\Users\haktan\Documents\SmartNews

## 1) Current Production State

- Pipeline: GitHub Actions cron every 6 hours (`.github/workflows/pipeline.yml`) is active.
- DB persistence: DuckDB file is persisted in GitHub Releases (`db-latest` asset: `smartnews.duckdb`).
- API: Live on Render.
  - URL: `https://smartnews-api.onrender.com`
  - Health: `/health`
- Frontend: Live on Vercel (project deployed and reachable).
  - Note: exact aliased URL can change per Vercel settings; check Vercel dashboard for canonical domain.

Live symptom snapshot (2026-04-04, latest checks):
- `/api/home` -> `top_stories=10`
- `/api/narratives?limit=20` -> `11`
- `/api/stories?limit=20` -> currently `1` on live (despite local improvements)
- A legacy story ID can still return pending-style summary on some live instances during rollout lag.

## 2) What Is Implemented

- DuckDB migration is complete (pipeline + API).
- Claim extraction pipeline exists: `pipeline/04b_claim_extraction.py`.
- Claims API exists: `GET /api/story/{story_id}/claims`.
- Story detail page consumes claims and renders verification section.
- Full-text quality gates were added in serving projection to reduce low-quality cards:
  - filters require non-empty title
  - `has_full_text = TRUE`
  - minimum full text length guard
- Workflow features:
  - manual trigger (`workflow_dispatch`) with `skip_scraping` and `skip_enrichment`
  - concurrency lock (`group: pipeline`)
  - scraping step can fail without stopping entire run (`continue-on-error: true`)
  - step summary output in GitHub Actions
- Frontend resilience hardening (2026-04-04):
  - `frontend/app/sources/page.tsx` now handles API failure + empty leaderboard state.
  - `frontend/app/page.tsx` narratives section now guards against malformed payloads.
  - `frontend/app/topic/[name]/page.tsx` now handles search API failure safely.
  - `frontend/app/narratives/[arcId]/page.tsx` timeline render now guards missing article arrays.
- API startup DB sync hardening (2026-04-04):
  - `api/main.py` now syncs DB from GitHub Releases on startup by default.
  - Falls back to existing local DB if sync fails and local file exists.
  - New setting in `api/config.py`: `DB_SYNC_ON_STARTUP` (default `true`).

## 3) Pipeline Run Order (Do Not Change)

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

## 4) Local LLM Mode (Claim Extraction)

`pipeline/04b_claim_extraction.py` supports local OpenAI-compatible providers.

Recommended with RTX 3060 Ti:

```bash
CLAIM_LLM_PROVIDER=local
CLAIM_MODEL=qwen2.5:7b-instruct
LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_OPENAI_API_KEY=ollama
```

Then run:

```bash
uv run python pipeline/04b_claim_extraction.py
```

Execution boundary (critical):
- Local Ollama mode works only when this command runs on the same machine as Ollama.
- GitHub-hosted Actions and remote agents cannot use your local `127.0.0.1` endpoint.
- For CI/remote runs, provide `OPENAI_API_KEY` or a reachable hosted/self-hosted LLM API endpoint.

## 5) Known Risks / Open Items

- `docs/PRODUCT_VALIDATIONS.md` is legacy/stale (Databricks-era checks). Keep as archive/reference only.
- Enrichment in GitHub-hosted CI still depends on available OpenAI credentials.
  - If `OPENAI_API_KEY` is absent, enrichment/claim/compilation steps are skipped by design.
  - Local Llama mode requires local/self-hosted execution boundary and is not usable from GitHub-hosted runners.
- Render free-tier cold starts and transient 502/connection-closed responses can still occur.
- Deployment skew risk (current top issue): API code and synced DB may not roll out atomically on Render free tier.
  - Observed behavior: list endpoint reflects new filtering while certain old story IDs still return pending summary text.
  - Latest commits attempted to hard-block pending placeholders at API level, but live instance behavior remains partially stale.
- Recent workflow failure root cause (run `23968498060`): `OPENAI_API_KEY` missing during `04_ai_enrichment.py`.
- Fix applied:
  - `pipeline/04_ai_enrichment.py` now supports `AI_LLM_PROVIDER=local` (OpenAI-compatible endpoint).
  - `.github/workflows/pipeline.yml` enrichment steps now run when either `AI_LLM_PROVIDER=local` or `OPENAI_API_KEY` exists.
  - Added workflow warning that GitHub-hosted runners cannot reach local `localhost` endpoints.
- Local Llama recovery status (latest):
  - `pipeline/04_ai_enrichment.py` rerun with local provider produced `gold.compiled_stories=1`.
  - `pipeline/05_serving_projection.py` rerun produced `serve.compiled_stories=1` and `serve.daily_briefing=ok`.
  - Updated `smartnews.duckdb` uploaded to GitHub Release asset `db-latest`.
  - After forced API redeploy and sync, live endpoints confirmed refreshed data.
  - Current verified snapshot (2026-04-04):
    - `/api/briefing/daily` -> 200 (`article_count=7`)
    - `/api/narratives?limit=5` -> `narratives_count=1`
    - `/api/stories?limit=5` -> `stories_count=1`
  - Frontend regression sweep passed on key routes: `/`, `/briefing`, `/narratives`, `/stories`, `/sources`, `/search?q=ai`.

## 6) First Tasks For Next Agent (Priority)

1. Resolve production rollout skew for stories endpoints (highest priority):
  - Confirm Render deployed commit is >= `53e93b0` (and latest follow-up commits).
  - If stale, force full service redeploy/restart and verify `/openapi.json` plus `/api/story/{old_id}` behavior.
  - Verify default `/api/story/{id}` returns 404 for pending-only rows unless `include_pending=true`.
2. Increase real compiled-story coverage so multi-source count does not drop to 1:
  - Run enrichment/claim/compilation pass with available model credentials.
  - Ensure `gold.compiled_stories` > 1 and `serve.compiled_stories` > 1 without placeholders.
3. Keep a rolling validation cadence (pipeline + API + frontend smoke) and append results to `docs/VALIDATIONS.md`.
4. Stabilize CI enrichment path:
   - either configure reliable OpenAI key usage,
   - or move enrichment-capable runs to self-hosted execution with reachable local/hosted LLM endpoint.
5. Add strict content-level post-run gates (`serve.daily_briefing`, `serve.story_arcs`, `serve.compiled_stories` non-empty thresholds).
6. Keep API redeploy/sync runbook handy for stale DB incidents and log each incident in `docs/LEARNINGS.md`.

## 10) Latest Commits (for next agent context)

- `d45f903` - Expand to broad-news feeds and non-tech taxonomy
- `3aad99e` - Expand story matching coverage and refresh deploy sync
- `c3df3d7` - Restore compiled story quality and hide pending placeholders
- `9cb0d32` - Disable pending fallback for story detail by default
- `c3f32e0` - Force API redeploy for story detail fallback fix
- `4ccdd14` - Require compiled body for story detail by default
- `559a57c` - Block pending story placeholders in API and UI
- `53e93b0` - Hard-block pending placeholder stories at API layer

## 7) Important File Map

- Pipeline core: `pipeline/`
- Validation script: `pipeline/validate.py`
- Claim extraction: `pipeline/04b_claim_extraction.py`
- Serving projection: `pipeline/05_serving_projection.py`
- API app: `api/`
- Frontend app: `frontend/`
- Operational docs: `docs/VALIDATIONS.md`, `docs/LEARNINGS.md`, `docs/AGENT_HANDOFF.md`

## 8) Guardrails

- Do not commit `.env`, `.mcp.json`, or `smartnews.duckdb`.
- API must read from `serve.*` tables only.
- Always run `uv run python ...` for pipeline scripts.
- After schema/serve changes, run `uv run python pipeline/validate.py`.

## 9) Handoff Checklist

- [x] Repo is on `main`
- [x] Handoff doc updated to current production state
- [x] Click-tracker fallback API URL updated to Render
- [x] Live validation pass completed and documented (see `docs/VALIDATIONS.md` Iterations A-G)
