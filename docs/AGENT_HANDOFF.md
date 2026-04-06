# SmartNews - Agent Handoff

> Canonical handoff doc for the next agent.
> Last updated: 2026-04-06 (post incident triage, pre OpenClaw handoff)
> Repo: hacktan/smartnews
> Local path: c:\Users\haktan\Documents\SmartNews

## 1) Current Production State

- Pipeline: GitHub Actions cron every 6 hours (`.github/workflows/pipeline.yml`) is active.
- DB persistence: DuckDB file is persisted in GitHub Releases (`db-latest` asset: `smartnews.duckdb`).
- API: Live on Render.
  - URL: `https://smartnews-api.onrender.com`
  - Health: `/health` → `{"status":"ok"}` ✓ (verified 2026-04-06)
- Frontend: Live on Vercel.
  - URL: `https://frontend-chi-brown-98.vercel.app`
  - Loads correctly (verified 2026-04-06)

Live snapshot (2026-04-06, manually verified via API):
- `/api/home` → `top_stories=9`, `trending_topics=10`
- `/api/stories?limit=1` → story present (`story_id: 7e88abaa8ebffaf1031d58f612b9995c`)
- `/api/narratives?limit=1` → arc present (`arc_id: cluster-3`, topic: Space Exploration)
- `/api/clusters` → cluster list present (`cluster_id: 3`)
- Production Monitor: **no open incident** → passing ✓
- Pipeline cron: operational (self-hosted runner, Ollama local LLM) ✓

## 2) Open Incidents

### [hacktan/smartnews#1](https://github.com/hacktan/smartnews/issues/1) — User Journey Monitor Failure

- **Status**: OPEN (unresolved)
- **First failure**: 2026-04-04T19:09 UTC (same day the monitor was added)
- **Last failure**: 2026-04-06T08:09 UTC (2 comments since opening = 3 total failures)
- **Workflow**: `.github/workflows/user_journey_monitor.yml` — runs every 6 hours on `ubuntu-latest`
- **What it does**: Playwright Chromium (desktop + mobile Chrome) navigates live Vercel frontend, catches `console.error`, `pageerror`, `requestfailed`, HTTP 5xx
- **What's healthy**: API endpoints all respond correctly. Python smoke/contract/data-quality checks pass (monitor.yml).
- **Root cause**: Unknown — actual Playwright error is only visible in the `playwright-live-report` artifact attached to each failing run.
  - Check: https://github.com/hacktan/smartnews/actions/workflows/user_journey_monitor.yml
  - Download `playwright-live-report` artifact from the latest failing run to see exact route + error
- **Likely candidates**: Render cold start causing SSR timeout, Next.js console.error from a client component, or a requestfailed event from a non-RSC prefetch in mobile Chrome
- **Task card**: See T5 in `docs/ROADMAP.md`

## 3) What Is Implemented

- Full DuckDB migration complete (pipeline + API).
- Pipeline: bronze → silver → gold → AI enrichment → story matching → claim extraction → serving projection.
- Claim extraction: `pipeline/04b_claim_extraction.py` + `GET /api/story/{story_id}/claims`.
- Story detail page renders verified claims.
- Full-text quality gates in serving projection (requires `has_full_text=TRUE`, min length).
- Frontend resilience hardening (sources, narratives, topics, search — all handle API failures gracefully).
- API startup DB sync from GitHub Releases on startup (`DB_SYNC_ON_STARTUP=true`).
- Quality automation:
  - `tests/smoke_api.py` — self-bootstrapping API smoke
  - `tests/contract_api.py` — strict response-key contract checks
  - `tests/smoke_frontend.py` — frontend route smoke
  - `tests/live_data_quality.py` — duplicate/placeholder/staleness anomaly checks
  - `.github/workflows/quality_gate.yml` — push/PR guardrail
  - `.github/workflows/monitor.yml` — production smoke every 2 hours (auto-opens incident issues)
  - `.github/workflows/user_journey_monitor.yml` — Playwright E2E every 6 hours (**currently failing**)
  - `frontend/e2e/user_journey.spec.ts` — browser-level journey test

## 4) Pipeline Run Order (Do Not Change)

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

04 runs twice: first for article enrichment + embeddings, second (after story matching) for story compilation only.

## 5) Infrastructure

### Self-hosted Runner (Windows machine)
- Runner label: `self-hosted`
- Installed at: `C:\actions-runner\`
- Auto-starts on login via Startup folder shortcut
- Requires Ollama running locally for AI enrichment (`http://127.0.0.1:11434/v1`)
- Model: `qwen2.5:7b-instruct`
- **If runner goes offline**: pipeline queues until machine comes back online
- **If pipeline crashes mid-run**: runner process may die (Ollama CPU starvation). Re-run `C:\actions-runner\run.cmd` or rely on next login.

### GitHub MCP (for agent tooling)
- Configured in `.mcp.json` (gitignored — never commit)
- Uses `@modelcontextprotocol/server-github` with `GITHUB_PERSONAL_ACCESS_TOKEN`
- **Do NOT use `gh` CLI** — it is not authenticated on this machine. Use MCP GitHub tools exclusively (`mcp__github__*`).

### DuckDB MCP
- Configured in `.mcp.json`
- `mcp-server-duckdb` with `--db-path ./smartnews.duckdb`
- Useful for direct DB inspection without writing Python scripts

## 6) Local LLM Mode (Claim Extraction)

`pipeline/04b_claim_extraction.py` supports local OpenAI-compatible providers.

Recommended with RTX 3060 Ti:

```bash
CLAIM_LLM_PROVIDER=local
CLAIM_MODEL=qwen2.5:7b-instruct
LOCAL_OPENAI_BASE_URL=http://127.0.0.1:11434/v1
LOCAL_OPENAI_API_KEY=ollama
```

Execution boundary (critical):
- Local Ollama mode only works when running on the same machine as Ollama.
- GitHub-hosted Actions runners cannot reach `127.0.0.1:11434`.

## 7) Known Risks / Open Items

- **User journey monitor failing** (hacktan/smartnews#1) — highest priority fix for next agent.
- **Self-hosted runner dependency**: CI requires user's Windows machine online with Ollama. If offline, pipeline queues.
- **Runner crash risk**: Ollama CPU starvation can kill runner mid-pipeline. `ENRICHMENT_BATCH_LIMIT=20` mitigates but doesn't eliminate.
- **Render cold start**: Render free-tier cold starts (10-30s) can cause Playwright test timeouts.
- **Fulltext scraping coverage**: ~18% (174/945). Improves over time. Validation threshold at 10%.
- **uv cache 400**: GitHub cache service rejects uv cache saves on self-hosted runner — cosmetic, no impact.
- `docs/PRODUCT_VALIDATIONS.md` is legacy/stale (Databricks-era). Keep as archive only.

## 8) First Tasks For Next Agent (Priority)

1. **Fix user journey monitor** — hacktan/smartnews#1 (see T5 in ROADMAP):
   - Go to: https://github.com/hacktan/smartnews/actions/workflows/user_journey_monitor.yml
   - Download `playwright-live-report` artifact from latest failing run
   - Read the actual Playwright error (names the failing route and error type)
   - Fix: the frontend bug OR loosen the test for known-flaky patterns
   - Close issue #1 after verified pass

2. **Raise fulltext scraping coverage** (T3 in ROADMAP):
   - Current: ~18%. Consider raising `SCRAPE_BATCH_LIMIT` from 100 → 200 if runner handles it.

3. **Keep rolling validation cadence**: append results to `docs/VALIDATIONS.md` after each significant change.

## 9) File Map

| What | Where |
|---|---|
| Pipeline scripts | `pipeline/` |
| Validation script | `pipeline/validate.py` |
| API app | `api/` |
| Frontend app | `frontend/` |
| Smoke/contract/quality tests | `tests/` |
| E2E Playwright test | `frontend/e2e/user_journey.spec.ts` |
| Playwright config | `frontend/playwright.config.ts` |
| Quality gate workflow | `.github/workflows/quality_gate.yml` |
| Production monitor | `.github/workflows/monitor.yml` |
| User journey monitor | `.github/workflows/user_journey_monitor.yml` |
| Main pipeline workflow | `.github/workflows/pipeline.yml` |
| Strategic roadmap | `docs/ROADMAP.md` |
| This handoff doc | `docs/AGENT_HANDOFF.md` |
| Operational validations log | `docs/VALIDATIONS.md` |
| Learnings | `docs/LEARNINGS.md` |

## 10) Guardrails

- Do NOT commit `.env`, `.mcp.json`, or `smartnews.duckdb`.
- API must read from `serve.*` tables only.
- Always run `uv run python ...` for pipeline scripts (never bare `python`).
- After schema/serve changes, run `uv run python pipeline/validate.py`.
- Do NOT trigger old Databricks pipeline — decommissioned, costs money.
- Do NOT use `gh` CLI for GitHub operations — use MCP tools (`mcp__github__*`).

## 11) Handoff Checklist

- [x] Repo is on `main`, clean working tree
- [x] Handoff doc updated to 2026-04-06
- [x] API verified live and healthy (2026-04-06)
- [x] Open incident documented (hacktan/smartnews#1)
- [x] Roadmap updated with T5 (Playwright fix task card)
- [x] VALIDATIONS.md updated with 2026-04-06 snapshot
- [ ] User journey monitor (hacktan/smartnews#1) — **unresolved, first task for next agent**

## 12) Latest Commits

- `e56b1f7` - Stabilize user journey monitor timeout and retry sleep ← HEAD
- `ba5f9ad` - Document latest automation stabilization and run outcomes
- `b23e122` - Add live data-quality checks and harden frontend/runtime monitoring
- `5af9427` - Record automation run outcomes and validation notes
- `bf6d478` - Add API contract checks and harden user-journey automation

## 13) Automation Snapshot (2026-04-06)

| Check | Status |
|---|---|
| API health | ✓ passing |
| Production Monitor (monitor.yml) | ✓ no open incident |
| Quality Gate (quality_gate.yml) | ✓ last known pass 2026-04-04 |
| User Journey Monitor (user_journey_monitor.yml) | ✗ FAILING — hacktan/smartnews#1 |
| Pipeline cron (pipeline.yml) | ✓ operational |
