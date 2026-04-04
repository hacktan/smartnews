# LEARNINGS

Practical notes and gotchas discovered while operating SmartNews.

## Pipeline

- Run order is strict. `03b_story_matching.py` depends on embeddings from `04_ai_enrichment.py` pass 1.
- `04b_claim_extraction.py` should run after `03b_story_matching.py` so claims can be attached to `story_id`.
- `05_serving_projection.py` is a full refresh for `serve.*` tables. Any new serve table must be created and fully rebuilt there.

## DuckDB

- Keep schema evolution idempotent. For added columns in existing tables, check `information_schema.columns` before `ALTER TABLE`.
- Store JSON payloads as strings in DuckDB and parse in API/frontend as needed.
- Use read-only API connections (`duckdb.connect(..., read_only=True)`) for safer runtime behavior.

## OpenAI integration

- Use `response_format={"type":"json_object"}` for extraction tasks to reduce parser failures.
- Clamp numeric scores/confidence into `[0.0, 1.0]` before writing to DB.
- Mark rows as processed even when extracted claim count is zero, otherwise pipeline reprocesses the same records forever.
- `pipeline/04_ai_enrichment.py` now supports `AI_LLM_PROVIDER=local` with OpenAI-compatible endpoints (e.g. Ollama/vLLM).
- GitHub-hosted Actions cannot call your local `127.0.0.1`; local Llama mode in CI requires either a self-hosted runner or a reachable network endpoint.

## Local LLM for claims (RTX 3060 Ti)

- `pipeline/04b_claim_extraction.py` supports `CLAIM_LLM_PROVIDER=local` with OpenAI-compatible local servers.
- Good default for 8GB VRAM: `qwen2.5:7b-instruct` (via Ollama).
- Scope clarification:
  - Works when pipeline runs on your own machine (where Ollama is running).
  - Does NOT work on GitHub-hosted Actions runners with `LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1`.
  - Does NOT work for remote agents that cannot access your local network/processes.
  - For CI usage, use either `OPENAI_API_KEY` or a publicly reachable/self-hosted LLM endpoint.
- Recommended env for local mode:
  - `CLAIM_LLM_PROVIDER=local`
  - `CLAIM_MODEL=qwen2.5:7b-instruct`
  - `LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1`
  - `LOCAL_OPENAI_API_KEY=ollama`
- If extraction fails in local mode, first check:
  - local server process is running (`ollama serve`)
  - model is installed (`ollama pull qwen2.5:7b-instruct`)
  - base URL and model name match local server config.

## Deployment

- Render free instance can cold start; temporary API latency spikes are expected.
- Vercel may serve previous deployment until alias update completes; verify using both deployment URL and aliased URL.
- If frontend routes return 500 while API is healthy, check server-component-incompatible handlers first (for example `onError` inside server component markup).
- API now supports startup DB sync (`DB_SYNC_ON_STARTUP`, default `true`) so new deployments refresh `smartnews.duckdb` from `db-latest` automatically.
- If live API data looks stale while local DB is current, redeploy/restart API service to trigger startup sync.

## Validation discipline

- Always run `uv run python pipeline/validate.py` after pipeline/schema changes.
- For frontend/API changes, run both:
  - local build (`npm run build`)
  - live smoke checks (`/`, `/stories`, `/story/<id>`, `/api/story/<id>/claims`).

## Frontend resilience learnings (2026-04-04)

- A route can look "empty" even when API returns `200`; some endpoints may return valid but empty payloads (`items: []`).
- Multi-source surfaces (`/stories`, `/narratives`, `/briefing`) need explicit no-data states because data can legitimately be missing between pipeline runs.
- For server components, every optional API segment should be guarded (`Array.isArray`, null-safe fallbacks) to prevent full-page render failures.
- `404` from `/api/briefing/daily` is a normal operational state when no briefing has been generated yet; frontend should treat it as a friendly empty state, not an error page.

## Documentation discipline

- Keep operational truth in:
  - `docs/VALIDATIONS.md` for checks and commands
  - `docs/LEARNINGS.md` for runbook-style lessons and pitfalls
- Archive old strategy docs under `docs/archive/`; keep `docs/` root focused on current stack.
