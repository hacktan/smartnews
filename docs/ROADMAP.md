# SmartNews Roadmap (Agent-Executable)

Last updated: 2026-04-04
Owner model: planning-first, execution-by-task-cards

## 1) Objective

Build a self-correcting SmartNews system where:
- Small regressions are caught automatically (API, frontend, data quality, freshness).
- Tasks are executable by lower-capability models with clear boundaries.
- Every task has explicit validation and exit criteria.

## 2) Quality Architecture

Quality is enforced in 3 layers:

1. Pre-merge gate (`.github/workflows/quality_gate.yml`)
- Backend local smoke against booted API.
- Frontend lint + production build.
- Blocks regressions before merge.

2. Production monitor (`.github/workflows/monitor.yml`)
- Runs every 2 hours against live API + Vercel frontend.
- Auto-opens/updates incident issue with smoke logs on failure.

3. Data integrity gate (`pipeline/validate.py`)
- Runs at pipeline end.
- Guards serving tables, score sanity, freshness/coverage thresholds.

## 3) Agent Execution Contract

Every implementation task must include:
- Scope: exact files and boundaries.
- Preconditions: what must already exist.
- Steps: atomic actions (max 5-7 steps).
- Validation: copy-paste commands + pass criteria.
- Rollback: what to revert if validation fails.

Definition of Done (global):
- Code implemented.
- Local validation commands passed.
- Relevant docs updated.
- Handoff note added to `docs/AGENT_HANDOFF.md`.

## 4) Task Cards (Priority Order)

## T1 - Stabilize API Contract Checks

Scope:
- `tests/smoke_api.py`
- `api/routers/*` (only if smoke failures expose contract drift)

Preconditions:
- API starts locally (`uv run uvicorn api.main:app`).

Steps:
1. Run smoke against local API.
2. Fix only contract-breaking routes (status/shape/null handling).
3. Re-run smoke.
4. Add regression assertions into smoke script when new bug class discovered.

Validation:
```bash
uv run uvicorn api.main:app --host 127.0.0.1 --port 8000
uv run python tests/smoke_api.py http://127.0.0.1:8000
```
Pass criteria:
- `FAIL=0` in smoke summary.

Rollback:
- Revert router-level changes if smoke gets worse than baseline.

## T2 - Stabilize Frontend Route Safety

Scope:
- `frontend/app/**/page.tsx`
- `tests/smoke_frontend.py`

Preconditions:
- API URL configured.

Steps:
1. Run route smoke.
2. Add/strengthen empty/error states for failing pages.
3. Keep dynamic pages resilient to missing API payload sections.
4. Re-run lint/build/smoke.

Validation:
```bash
cd frontend
npm ci
npm run lint
npm run build
cd ..
uv run python tests/smoke_frontend.py https://frontend-chi-brown-98.vercel.app --api https://smartnews-api.onrender.com
```
Pass criteria:
- frontend smoke `FAIL=0`
- lint/build successful

Rollback:
- Revert page-level changes causing SSR/render crashes.

## T3 - Raise Enrichment & Fulltext Coverage Safely

Scope:
- `pipeline/01b_fulltext_scraping.py`
- `pipeline/04_ai_enrichment.py`
- `pipeline/validate.py`

Preconditions:
- Baseline metrics recorded from current pipeline run.

Steps:
1. Increase coverage incrementally (small batch changes).
2. Keep runner stability first (no OOM/starvation).
3. Tune only realistic validation thresholds.
4. Record before/after metrics.

Validation:
```bash
uv run python pipeline/01b_fulltext_scraping.py
uv run python pipeline/04_ai_enrichment.py
uv run python pipeline/05_serving_projection.py
uv run python pipeline/validate.py
```
Pass criteria:
- Validation exits 0.
- Coverage metrics non-decreasing vs baseline.

Rollback:
- Restore previous batch limits/provider settings when runner reliability drops.

## T4 - Incident Workflow Hygiene

Scope:
- `.github/workflows/monitor.yml`
- `docs/VALIDATIONS.md`

Preconditions:
- Monitor workflow present and scheduled.

Steps:
1. Trigger monitor manually.
2. Verify logs artifact upload.
3. Verify failure path opens/updates single incident issue.
4. Document run behavior.

Validation:
- GitHub Actions run succeeds in healthy state.
- On forced failure test, one open incident thread is reused.

Rollback:
- Disable issue-creation step if it generates noisy duplicates.

## 5) Automation Rule for "Small Problems"

When any new bug is found manually:
1. Fix the bug.
2. Add one automated check that would have caught it.
3. Add the check to a recurring path (quality gate or monitor).
4. Record in `docs/VALIDATIONS.md` with date and command.

This prevents repeating manual, one-off debugging.

## 6) Weekly Validation Cadence

Minimum weekly routine:

1. Run full pipeline + `pipeline/validate.py`.
2. Run local API smoke.
3. Check latest production monitor run and open incident issues.
4. Update `docs/AGENT_HANDOFF.md` with current counts and risks.

## 7) Short Backlog (After Stability)

1. Add lightweight schema contract test (response key presence per endpoint).
2. Add synthetic data seed for deterministic local smoke mode.
3. Add trend-based alerts (coverage drop > X% week-over-week).
4. Add frontend Playwright journey smoke for top 3 user paths.
