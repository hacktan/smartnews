# SmartNews - Agent Handoff

> Canonical handoff doc for the next agent.
> Last updated: 2026-04-04
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

- User reported frontend quality regressions (blank titles in Top Stories, some pages still showing RSS-like summaries instead of full-text-backed content).
- Need another end-to-end product validation pass after latest pipeline run:
  - pipeline validation
  - API smoke
  - frontend smoke on live routes
- `docs/PRODUCT_VALIDATIONS.md` is legacy/stale (contains old Databricks-era checks). Keep for reference only or archive/update.
- Live API currently returns:
  - `/api/briefing/daily` => `404` (no latest briefing row)
  - `/api/narratives?limit=1` => `items: []`
  - `/api/stories?limit=1` => `items: []`
  This is the main reason for currently sparse/empty multi-source pages.
- Recent workflow failure root cause (run `23968498060`): `OPENAI_API_KEY` missing during `04_ai_enrichment.py`.
- Fix applied:
  - `pipeline/04_ai_enrichment.py` now supports `AI_LLM_PROVIDER=local` (OpenAI-compatible endpoint).
  - `.github/workflows/pipeline.yml` enrichment steps now run when either `AI_LLM_PROVIDER=local` or `OPENAI_API_KEY` exists.
  - Added workflow warning that GitHub-hosted runners cannot reach local `localhost` endpoints.
- Recovery status (latest):
  - Workflow run `23968702286` completed successfully.
  - Release upload succeeded after workflow `permissions: contents: write` fix.
  - Live snapshot after run: `narratives_count=1`, `stories_count=0`, `briefing=404`.
- Local Llama recovery status (latest):
  - `pipeline/04_ai_enrichment.py` rerun with local provider produced `gold.compiled_stories=1`.
  - `pipeline/05_serving_projection.py` rerun produced `serve.compiled_stories=1` and `serve.daily_briefing=ok`.
  - Updated `smartnews.duckdb` uploaded to GitHub Release asset `db-latest`.
  - After forced API redeploy, live endpoints confirmed refreshed data:
    - `/api/briefing/daily` -> 200 (`article_count=7`)
    - `/api/stories?limit=3` -> `stories_count=1`
  - Frontend regression sweep passed on key routes: `/`, `/briefing`, `/narratives`, `/stories`, `/sources`, `/search?q=ai`.

## 6) First Tasks For Next Agent (Priority)

1. Run fresh pipeline (or trigger workflow) and verify `pipeline/validate.py` passes.
2. Confirm `serve.daily_briefing`, `serve.story_arcs`, `serve.compiled_stories` receive non-empty rows.
3. Re-run live API smoke checks and capture counts, not just status codes.
4. Inspect live multi-source routes (`/briefing`, `/narratives`, `/stories`) for data-populated rendering.
5. If data is still missing, patch generation steps in `pipeline/03b_story_matching.py`, `pipeline/04_ai_enrichment.py`, and `pipeline/05_serving_projection.py`.
6. If live API still shows stale data after DB release update, force API restart/redeploy so startup DB sync pulls latest `db-latest` asset.

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
- [ ] Next agent to run full live validation pass and document outcomes
