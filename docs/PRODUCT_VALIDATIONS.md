# SmartNews — Product Validations

This document defines the validation checklist for each layer of the SmartNews platform.
An agent or developer must run through the relevant section before considering a layer complete.
If a validation fails, the layer is NOT done — fix and re-validate.

---

## How to Use This Document

- Before starting a new layer, read its validation criteria to understand the exit conditions.
- After completing a layer, run every check in order.
- Mark checks with [x] when confirmed.
- If a check cannot be confirmed, note the blocker inline.
- Do not proceed to the next layer until the current layer passes all required checks.

---

## Layer 0 — Data Foundation

### Pipeline Validation
- [ ] Bronze table `dbc_mcp_projects.bronze.rss_raw` exists and is queryable
- [ ] Silver table `dbc_mcp_projects.silver.rss_cleaned` exists and is queryable
- [ ] Gold tables exist: `gold.news_articles`, `gold.daily_category_summary`, `gold.daily_source_summary`
- [ ] All three Databricks notebooks exist in GitHub repo under `notebooks/`
- [ ] Job `SmartNews_Daily_Pipeline` exists and is scheduled
- [ ] Last job run status = SUCCESS (check via Databricks UI or API)

### Data Quality Validation
- [ ] `SELECT COUNT(*) FROM bronze.rss_raw` returns > 0 rows
- [ ] `SELECT COUNT(*) FROM silver.rss_cleaned` returns > 0 rows
- [ ] `SELECT COUNT(*) FROM gold.news_articles` returns > 0 rows
- [ ] Bronze deduplication works: running pipeline twice does not double-count rows
- [ ] Silver contains no HTML tags in `clean_summary` field
- [ ] Gold articles have `category` populated (no NULLs)
- [ ] Gold `daily_category_summary` has at least 3 distinct categories

### Pipeline Behavior Validation
- [ ] MERGE INTO Bronze: duplicate `entry_id` is skipped, not duplicated
- [ ] MERGE INTO Silver: only Bronze records not in Silver are processed
- [ ] Gold partition overwrite: running again for same date does not add rows, only replaces
- [ ] If no new Bronze records exist, Silver exits gracefully (not an error)

---

## Layer 1 — AI Enrichment

### Schema Validation
- [ ] `gold.news_articles` contains column `ai_summary` (STRING)
- [ ] `gold.news_articles` contains column `hype_score` (DOUBLE, range 0.0–1.0)
- [ ] `gold.news_articles` contains column `credibility_score` (DOUBLE, range 0.0–1.0)
- [ ] `gold.news_articles` contains column `importance_score` (DOUBLE, range 0.0–1.0)
- [ ] `gold.news_articles` contains column `entities` (STRING, JSON array or comma-separated)
- [ ] `gold.news_articles` contains column `subtopic` (STRING)
- [ ] `gold.news_articles` contains column `language` (STRING)
- [ ] `gold.news_articles` contains column `enriched_at` (TIMESTAMP)

### Score Range Validation
```sql
-- All of these should return 0 rows
SELECT COUNT(*) FROM gold.news_articles WHERE hype_score < 0 OR hype_score > 1;
SELECT COUNT(*) FROM gold.news_articles WHERE credibility_score < 0 OR credibility_score > 1;
SELECT COUNT(*) FROM gold.news_articles WHERE importance_score < 0 OR importance_score > 1;
```
- [ ] hype_score out-of-range count = 0
- [ ] credibility_score out-of-range count = 0
- [ ] importance_score out-of-range count = 0

### Coverage Validation
```sql
-- Should be > 80% of total articles
SELECT
  COUNT(CASE WHEN ai_summary IS NOT NULL AND ai_summary != '' THEN 1 END) * 100.0 / COUNT(*) AS summary_coverage_pct,
  COUNT(CASE WHEN hype_score IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) AS hype_coverage_pct
FROM gold.news_articles;
```
- [ ] `ai_summary` coverage > 80%
- [ ] `hype_score` coverage > 80%
- [ ] `credibility_score` coverage > 80%

### Enrichment Quality Spot Check (Manual)
- [ ] Pick 5 random articles and read their `ai_summary` — summaries must be coherent English sentences, not truncated or hallucinated
- [ ] Pick 5 articles with high `hype_score` (> 0.7) — titles should intuitively feel like clickbait or exaggerated
- [ ] Pick 5 articles with low `hype_score` (< 0.3) — titles should feel measured and factual
- [ ] `entities` field is not empty for articles that clearly mention companies or people

### Pipeline Behavior Validation
- [ ] AI enrichment only processes articles not yet enriched (incremental, not full re-run)
- [ ] If Azure OpenAI API is unavailable, the notebook fails gracefully with a clear error — it does NOT silently write NULLs for all articles
- [ ] Re-running enrichment on already-enriched articles does not overwrite existing scores

---

## Layer 2 — Serving Projection

### Schema Validation
- [ ] Schema `dbc_mcp_projects.serve` exists
- [ ] Table `serve.article_cards` exists with columns: `entry_id`, `title`, `source_name`, `published_at`, `category`, `summary_snippet`, `hype_score`, `credibility_score`, `importance_score`, `link`, `publish_date`
- [ ] Table `serve.category_feeds` exists with columns: `entry_id`, `category`, `published_at`, `importance_score`, `hype_score`, `title`, `summary_snippet`, `source_name`
- [ ] Table `serve.trending_topics` exists with columns: `topic`, `article_count`, `top_source`, `latest_at`, `category`
- [ ] Table `serve.article_detail` exists with full enriched fields including `entities`, `ai_summary`, `related_entry_ids`

### Data Freshness Validation
```sql
-- Should return a timestamp within the last 5 hours (after pipeline schedule change)
SELECT MAX(updated_at) FROM serve.article_cards;
```
- [ ] `serve.article_cards` updated within last 5 hours
- [ ] `serve.category_feeds` updated within last 5 hours

### Query Performance Validation
- [ ] `SELECT * FROM serve.article_cards ORDER BY published_at DESC LIMIT 20` completes in < 3 seconds on SQL Warehouse
- [ ] `SELECT * FROM serve.category_feeds WHERE category = 'AI & Machine Learning' ORDER BY importance_score DESC LIMIT 20` completes in < 3 seconds
- [ ] `SELECT * FROM serve.trending_topics LIMIT 10` completes in < 2 seconds

### Serving Data Integrity
- [ ] `serve.article_cards` row count matches `gold.news_articles` row count (no articles dropped in projection)
- [ ] No NULL values in `serve.article_cards.entry_id`
- [ ] No NULL values in `serve.article_cards.title`
- [ ] `summary_snippet` is truncated to ≤ 200 characters (card-safe)
- [ ] `hype_score` and `credibility_score` are present in serving tables, not computed at query time

### Pipeline Frequency Validation
- [ ] Databricks Job schedule updated to run every 4 hours (6 runs per day)
- [ ] Confirm 2 consecutive runs both succeed without errors

---

## Layer 3 — API Layer

### Deployment Validation
- [ ] API is deployed and reachable from public URL (or VPN if internal)
- [ ] API is not directly connecting to Databricks Gold tables — it queries Serve tables only
- [ ] All secrets are stored in Azure Key Vault, not in code or environment variables in plain text

### Endpoint Validation

#### GET /api/home
- [ ] Returns 200 OK
- [ ] Response contains `top_stories` array with ≥ 5 articles
- [ ] Response contains `category_rows` object with ≥ 3 categories
- [ ] Each article object in response contains: `id`, `title`, `source`, `published_at`, `category`, `summary_snippet`, `hype_score`, `credibility_score`, `link`
- [ ] Response time < 500ms (with cache hit)

#### GET /api/category/{slug}
- [ ] Returns 200 OK for valid category slug
- [ ] Returns 404 for invalid slug
- [ ] Supports `?page=` and `?limit=` query params
- [ ] Articles are sorted by `importance_score DESC` by default
- [ ] Response time < 800ms

#### GET /api/article/{id}
- [ ] Returns 200 OK for valid article ID
- [ ] Returns 404 for unknown ID
- [x] Response contains: `ai_summary`, `entities`, `hype_score`, `credibility_score`, `link`, `related_articles` array
- [x] `related_articles` array contains ≥ 1 article when related content exists

#### GET /api/search?q=
- [ ] Returns 200 OK with results for common tech keywords (e.g., "AI", "chip", "startup")
- [ ] Returns empty results array (not 500 error) for queries with no matches
- [ ] Supports `?category=`, `?source=`, `?from=`, `?to=` filter params
- [ ] Results are ordered by relevance or recency

#### POST /api/events/click
- [x] Returns 200 OK or 202 Accepted
- [x] Event is logged with: `article_id`, `timestamp`, `session_id` or `user_id`
- [x] Does not block the user-facing response (fire-and-forget or async)

### API Contract Validation
- [ ] API returns UI-ready payloads — no raw Delta table column names leaked to frontend
- [ ] Numeric scores are rounded to 2 decimal places in responses
- [ ] Missing AI fields return `null`, not 500 errors
- [ ] API supports CORS for the frontend domain

---

## Layer 4 — Web Frontend

### Homepage Validation
- [ ] Page loads in < 2 seconds (Lighthouse or manual measurement)
- [x] "Top Stories" section displays ≥ 5 article cards
- [x] At least 3 category row sections are visible
- [x] "Low Hype Picks" or "High Signal" section is visible and distinct from Top Stories
- [x] Each article card shows: title, source, time ago, category label, summary snippet, hype badge
- [x] Hype badge is visually distinct (color or icon) and uses soft language ("High hype risk", not "Fake")
- [x] Credibility indicator is visible on cards with high/low scores
- [ ] Page is fully responsive on 375px mobile width

### Category Page Validation
- [ ] All 8 categories from Silver are accessible via navigation
- [ ] Articles load correctly for each category
- [ ] Sorting options work (by recency, by importance)
- [ ] Pagination or "load more" works correctly
- [ ] Empty state is shown gracefully if a category has no articles

### Article Detail Page Validation
- [ ] `ai_summary` is displayed prominently (not just `clean_summary`)
- [x] `hype_score` and `credibility_score` are visible with soft label copy
- [x] `entities` are shown as clickable tags (if present)
- [x] "Read original article" link opens in new tab
- [x] Related articles section shows ≥ 1 related article
- [x] Page does not break if `ai_summary` or `entities` are null

### Search Validation
- [ ] Search returns results for "AI", "startup", "chip" within 2 seconds
- [ ] Category filter narrows results correctly
- [ ] Empty search returns an informative state, not a 500 error
- [ ] Search input is accessible via keyboard

### Event Tracking Validation
- [x] Clicking an article card fires `POST /api/events/click` (check browser Network tab)
- [ ] Opening article detail page logs a click event
- [x] Events are captured for anonymous users (no login required)
- [x] Event logging failure does not break the UI (errors are swallowed gracefully)

### UI Principle Validation (Manual Review)
- [ ] The site feels calm and structured — not a chaotic feed
- [ ] Every article has a visible reason for its placement (section label, badge, ranking cue)
- [ ] There is no infinite scroll without user control
- [ ] AI fields are visible to users — they are not hidden in the data layer

---

## Layer 5 — Product Intelligence (Phase 2)

### Topic Clustering Validation
- [ ] `serve.trending_topics` contains clusters with ≥ 2 articles per cluster
- [ ] Cluster names are human-readable topic labels, not article titles
- [ ] Homepage trending section shows clusters, not individual articles
- [ ] Article detail page links to its topic cluster page

### Related Stories Validation
- [ ] Related articles on detail page are semantically related (same topic or cluster), not just same category
- [ ] Related articles are not the article itself
- [ ] Related articles section handles gracefully when no related content exists

---

## Layer 6 — Personalization (Phase 3)

### Event Pipeline Validation
- [ ] Click, dwell, save, and hide events are stored in a queryable table
- [ ] Events table has `user_id` or `session_id`, `article_id`, `event_type`, `timestamp`
- [ ] Event data is not used until ≥ 3 interactions are logged for a user (cold start protection)

### Personalized Feed Validation
- [ ] `GET /api/feed/for-you` returns different results for users with different interaction histories
- [ ] The feed preserves category diversity — no single category dominates > 60% of results
- [ ] Users with no history receive the same as the default homepage (graceful cold start)

---

## Cross-Cutting Validations (Every Layer)

### Security
- [ ] No API keys or secrets are hardcoded in any file committed to GitHub
- [ ] `.env` is in `.gitignore`
- [ ] Databricks token is not exposed in logs or error messages

### Observability
- [ ] Every pipeline run logs: start time, end time, row counts per stage, any errors
- [ ] API layer logs: endpoint, response time, error codes
- [ ] Failed enrichment does not silently produce NULLs — it logs a warning with article ID

### Backward Compatibility
- [ ] Adding new AI enrichment fields to Gold does not break existing Serving projections
- [ ] Adding new Serving fields does not break API responses (optional fields)
- [ ] Adding new API fields does not break the Frontend (unused fields are ignored)

### Content Freshness
- [ ] After pipeline runs, new articles appear in `serve.article_cards` within 10 minutes
- [ ] Freshness metadata (`published_at`, `ingested_at`) is accurate and visible in the UI

---

## Agent Self-Validation Instructions

When an agent completes a task, it must:

1. Identify which layer the completed work belongs to.
2. Open this document and run through the relevant layer's checklist.
3. For data validations: execute the SQL queries and confirm results.
4. For API validations: make actual HTTP requests and inspect responses.
5. For UI validations: review the rendered page against the criteria.
6. Report which checks passed and which failed.
7. If any check fails: do not mark the layer as complete. Fix and re-validate.
8. Cross-reference PRODUCT_GOALS.md to ensure no product principles were violated.

A layer is complete only when **all required checks in its section pass**.
