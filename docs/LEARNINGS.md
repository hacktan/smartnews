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

## Local LLM for claims (RTX 3060 Ti)

- `pipeline/04b_claim_extraction.py` supports `CLAIM_LLM_PROVIDER=local` with OpenAI-compatible local servers.
- Good default for 8GB VRAM: `qwen2.5:7b-instruct` (via Ollama).
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

## Validation discipline

- Always run `uv run python pipeline/validate.py` after pipeline/schema changes.
- For frontend/API changes, run both:
  - local build (`npm run build`)
  - live smoke checks (`/`, `/stories`, `/story/<id>`, `/api/story/<id>/claims`).

## Documentation discipline

- Keep operational truth in:
  - `docs/VALIDATIONS.md` for checks and commands
  - `docs/LEARNINGS.md` for runbook-style lessons and pitfalls
- Archive old strategy docs under `docs/archive/`; keep `docs/` root focused on current stack.
