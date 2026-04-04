# Layer 8 — Multi-Source Full-Text Scraping + AI Content Compilation

> **STATUS**: HISTORICAL PLAN — Core implementation completed (see docs/AGENT_HANDOFF.md and docs/VALIDATIONS.md)
> **Created**: 2026-03-09
> **Purpose**: Upgrade SmartNews from 3-source RSS summaries to 20+ source full-text scraping with cross-source story matching and AI-compiled "best version" articles.

---

## 1. Why This Matters

Current SmartNews has a fundamental limitation: it only sees RSS summaries (1-3 sentences) from 3 sources. This means:
- AI scores (hype, credibility) are based on minimal context
- Story clustering is weak (not enough source diversity)
- Cross-source comparison is impossible
- No way to verify claims across sources

This upgrade makes SmartNews a true multi-perspective news intelligence platform.

---

## 2. Architecture Overview

### Current Pipeline (5 tasks)
```
bronze_ingestion → silver_transformation → gold_aggregation → ai_enrichment → serving_projection
```

### New Pipeline (7 tasks)
```
bronze_ingestion → fulltext_scraping → silver_transformation → gold_aggregation → story_matching → ai_enrichment → serving_projection
```

### New Capabilities
1. **20+ RSS sources** across tech, business, science, international
2. **Full article body** extracted via `trafilatura`
3. **Cross-source story matching** — identify when 3+ sources cover the same event
4. **AI-compiled stories** — synthesize "best version" from all source perspectives
5. **Claim verification** — track which sources confirm/dispute each factual claim

---

## 3. Phase 1 — Source Expansion (20+ RSS Feeds)

### New Feed List

**Tech (existing + new):**
| Source | Feed URL | Category |
|--------|----------|----------|
| BBC Tech | `http://feeds.bbci.co.uk/news/technology/rss.xml` | existing |
| NYT Tech | `https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml` | existing |
| The Verge | `https://www.theverge.com/rss/index.xml` | existing |
| Ars Technica | `http://feeds.arstechnica.com/arstechnica/index` | new |
| TechCrunch | `https://techcrunch.com/feed/` | new |
| Wired | `https://www.wired.com/feed/rss` | new |
| Engadget | `https://www.engadget.com/rss.xml` | new |
| MIT Tech Review | `https://www.technologyreview.com/feed/` | new |
| The Register | `https://www.theregister.com/headlines.atom` | new |

**General / Business / Science:**
| Source | Feed URL | Category |
|--------|----------|----------|
| Reuters | `https://www.reutersagency.com/feed/` | new |
| The Guardian Tech | `https://www.theguardian.com/technology/rss` | new |
| Hacker News | `https://hnrss.org/frontpage` | new |
| Science Daily | `https://www.sciencedaily.com/rss/top.xml` | new |
| Nature News | `http://feeds.nature.com/nature/rss/current` | new |

**International / Diverse:**
| Source | Feed URL | Category |
|--------|----------|----------|
| Al Jazeera | `https://www.aljazeera.com/xml/rss/all.xml` | new |
| DW (Deutsche Welle) | `https://rss.dw.com/rdf/rss-en-sci` | new |
| NHK World | `https://www3.nhk.or.jp/nhkworld/en/news/feeds/` | new |

### Schema Impact
- **None.** Existing `bronze.rss_raw` already has `feed_source` and `feed_url` columns. MERGE dedup on `entry_id` handles everything.

### Code Changes
- `01_bronze_ingestion.py`: Expand `RSS_FEEDS` list, add `User-Agent` header, add per-feed error isolation

### Volume Impact
- Current: ~30-60 articles/day (3 feeds)
- Projected: ~200-400 articles/day (20+ feeds)
- Consider raising `ENRICHMENT_BATCH_LIMIT` from 50 → 100 for faster catch-up

---

## 4. Phase 2 — Full-Text Scraping

### Library: `trafilatura`
Best-in-class article text extraction. Layout-agnostic, handles diverse sites, built-in `robots.txt` checking, actively maintained. Superior to abandoned `newspaper3k`.

### New Notebook: `notebooks/01b_fulltext_scraping.py`
Runs between bronze ingestion and silver transformation.

### New Table: `bronze.article_fulltext`
```sql
CREATE TABLE IF NOT EXISTS dbc_mcp_projects.bronze.article_fulltext (
  entry_id        STRING NOT NULL,
  full_text       STRING,
  text_length     INT,
  extraction_ok   BOOLEAN,
  extraction_err  STRING,
  source_domain   STRING,
  robots_allowed  BOOLEAN,
  scraped_at      TIMESTAMP,
  pipeline_run_id STRING
) USING DELTA
```

Separate table (not column on `rss_raw`) because:
1. Scraping may fail — don't complicate RSS MERGE
2. Full text is large (2-10KB) — keeps hot RSS table lean
3. Incremental: only scrape `entry_id`s not yet in this table

### Scraping Logic
```python
SCRAPE_BATCH_LIMIT = 50
SCRAPE_DELAY = 1.0  # polite scraping

# Only unscraped articles
df_pending = spark.sql("""
  SELECT b.entry_id, b.link, b.feed_source
  FROM bronze.rss_raw b
  LEFT JOIN bronze.article_fulltext f ON b.entry_id = f.entry_id
  WHERE f.entry_id IS NULL
  LIMIT {SCRAPE_BATCH_LIMIT}
""")

for row in df_pending.collect():
    robots_ok = trafilatura.check_url(row.link)
    if not robots_ok:
        # record robots_allowed=False, skip
        continue
    downloaded = trafilatura.fetch_url(row.link)
    text = trafilatura.extract(downloaded) if downloaded else None
    # store result
    time.sleep(SCRAPE_DELAY)
```

### Error Handling
| Scenario | Action |
|----------|--------|
| `robots.txt` blocks | Record `robots_allowed=False`, skip forever |
| HTTP 403/404/500 | Record error, retry once next run |
| Paywall / empty | `extraction_ok=False`, fallback to RSS summary |
| Timeout | 15s limit per request, log and skip |
| Domain rate limit | Max 5 articles per domain per run |

### Schema Changes Downstream

**Silver** — add columns:
```sql
full_text          STRING    -- from bronze.article_fulltext
has_full_text      BOOLEAN   -- extraction_ok flag
full_text_word_count INT     -- recomputed from full text
```

**Gold** — add columns:
```sql
full_text          STRING
has_full_text      BOOLEAN
```

**AI Enrichment prompt upgrade:**
```
Title: {title}
Summary: {summary}
Full Text (first 3000 chars): {full_text[:3000] if full_text else 'N/A'}
```

### Token Budget Impact
| Operation | Before | After |
|-----------|--------|-------|
| Chat enrichment/article | ~600 tokens | ~1500 tokens |
| Chat enrichment/run (50 articles) | ~30K tokens | ~75K tokens |
| Time at 10K TPM | ~3 min | ~8 min |

Still fits within 1800s task timeout.

---

## 5. Phase 3 — Cross-Source Story Matching

### Algorithm: 3-Tier Matching

**Tier 1 — Title Similarity (fast, cheap)**
- Normalize: lowercase, remove punctuation/stopwords
- Jaccard similarity on word sets
- Threshold: > 0.5 → candidate match

**Tier 2 — Embedding Cosine (semantic)**
- Use existing `text-embedding-3-small` vectors
- 48-hour sliding window
- Threshold: cosine > 0.85 → same story

**Tier 3 — Entity + Temporal Overlap (validation)**
- Shared entities from existing `entities` JSON column
- Published within 48h of each other
- Entity overlap > 50% → strong signal

**Union-Find grouping**: If A↔B and B↔C match, all three form one story.

### New Notebook: `notebooks/03b_story_matching.py`

### New Table: `gold.story_matches`
```sql
CREATE TABLE IF NOT EXISTS dbc_mcp_projects.gold.story_matches (
  story_id        STRING NOT NULL,   -- MD5 of sorted entry_ids
  entry_ids       STRING,            -- JSON array
  source_count    INT,
  sources         STRING,            -- JSON array
  canonical_title STRING,            -- from highest-credibility source
  match_method    STRING,            -- "title" | "embedding" | "entity" | "hybrid"
  match_score     DOUBLE,
  first_published TIMESTAMP,
  last_published  TIMESTAMP,
  category        STRING,
  matched_at      TIMESTAMP
) USING DELTA
```

### Performance
- 200-400 articles in 7-day window → ~80K pairwise comparisons → runs in seconds
- Embedding cosine function already exists in `05_serving_projection.py` → reuse

---

## 6. Phase 4 — AI Content Compilation

### Concept
For each story with 2+ sources, GPT-4o-mini synthesizes:
1. **Compiled title** — neutral, factual
2. **Compiled body** — 300-500 words, comprehensive, attributed
3. **Key claims** — which sources confirm/dispute each claim
4. **Consensus points** — facts all sources agree on
5. **Divergence points** — where sources disagree

### New Table: `gold.compiled_stories`
```sql
CREATE TABLE IF NOT EXISTS dbc_mcp_projects.gold.compiled_stories (
  story_id            STRING NOT NULL,
  compiled_title      STRING,
  compiled_summary    STRING,          -- 3-5 sentence synthesis
  compiled_body       STRING,          -- 300-500 word compiled article
  source_count        INT,
  sources_used        STRING,          -- JSON array
  key_claims          STRING,          -- JSON: [{claim, confirmed_by, disputed_by}]
  consensus_points    STRING,          -- JSON array
  divergence_points   STRING,          -- JSON array
  compiled_at         TIMESTAMP,
  model_used          STRING
) USING DELTA
```

### Compilation Prompt
```
You are an expert news editor synthesizing multiple source reports about the same story.

Given {N} sources covering the same event, produce a JSON:
{
  "compiled_title": "Clear, neutral headline (max 15 words)",
  "compiled_summary": "3-5 sentence synthesis from all sources",
  "compiled_body": "300-500 word article that:
    - Leads with confirmed facts
    - Attributes claims to sources ('According to BBC...')
    - Notes exclusive details from specific sources
    - Highlights factual disagreements between sources
    - Uses calm, factual language",
  "key_claims": [{
    "claim": "The factual claim",
    "confirmed_by": ["BBC", "NYT"],
    "disputed_by": [],
    "exclusive_to": null
  }],
  "consensus_points": ["Fact all sources agree on"],
  "divergence_points": ["Point where sources disagree, both sides cited"]
}

Rules:
- NEVER invent facts not in any source
- Prefer specificity: numbers, names, dates
- When sources conflict, present both with attribution
- Return ONLY the JSON
```

### Token Budget
| Metric | Value |
|--------|-------|
| Input per story | ~2000-3000 tokens (5 sources x 2000 chars each) |
| Output per story | ~800-1200 tokens |
| Stories per day (2+ sources) | ~10-30 |
| Time per batch (20 stories) | ~10-15 min |
| Cost per run | < $0.05 |

### Implementation
- New "Pass 3" in `04_ai_enrichment.py`
- Guard: `compiled_at IS NULL` on `gold.story_matches`
- Batch limit: 20 stories per run
- Sequential with 0.5s sleep (respects 10K TPM)

---

## 7. Phase 5 — Serve, API & Frontend

### New Serve Table: `serve.compiled_stories`
```sql
CREATE TABLE IF NOT EXISTS dbc_mcp_projects.serve.compiled_stories (
  story_id            STRING NOT NULL,
  compiled_title      STRING,
  compiled_summary    STRING,
  compiled_body       STRING,
  source_count        INT,
  sources_used        STRING,
  key_claims          STRING,
  consensus_points    STRING,
  divergence_points   STRING,
  entry_ids           STRING,
  category            STRING,
  first_published     TIMESTAMP,
  last_published      TIMESTAMP,
  compiled_at         TIMESTAMP
) USING DELTA
```

Also add `story_id` column to `serve.article_cards` and `serve.article_detail`.

### New API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stories` | List compiled stories, ordered by source_count + recency |
| GET | `/api/stories/{story_id}` | Full compiled story + individual source articles |

Modify existing:
- `GET /api/article/{id}` → add `story_id` + `other_source_coverage[]`
- `GET /api/home` → add `multi_source_stories` section

### New Frontend Routes

**`/story/[id]` — Compiled Story View**
1. Compiled title (large, bold)
2. Source count badges ("Covered by 4 sources")
3. Compiled summary (blue highlight)
4. Compiled body (full synthesized article)
5. Consensus section (green box)
6. Divergence section (amber box)
7. Key claims table (claim + which sources confirm/dispute)
8. Individual source article cards with score badges

**Article Detail Enhancement:**
- New section: "Other Sources Covering This Story" (2-4 cards)
- Link to `/story/{story_id}`

**Homepage Enhancement:**
- New section: "Multi-Source Stories" (top 3-5 compiled stories)

---

## 8. Implementation Timeline

| Phase | Days | What |
|-------|------|------|
| **1. Source Expansion** | 1-3 | Expand RSS feeds to 20+, deploy, verify |
| **2. Full-Text Scraping** | 4-8 | New notebook + table, Silver/Gold schema, prompt upgrade |
| **3. Story Matching** | 9-13 | 3-tier algorithm, Union-Find grouping |
| **4. AI Compilation** | 14-20 | Compilation pass, serve table, compiled stories |
| **5. API + Frontend** | 21-28 | Stories API, compiled story pages, multi-source UI |

---

## 9. Cost Estimate

| Item | Monthly Cost |
|------|-------------|
| OpenAI (enrichment + compilation) | ~$1-3 |
| Databricks compute (extra ~5 min/run) | ~$2-5 |
| Total infrastructure increase | **~$3-8/month** |

---

## 10. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| robots.txt blocks | Low | Graceful fallback to RSS summary |
| Paywall content | Low | Extract available text, flag as partial |
| False story matches | High | Require 2/3 tiers to agree |
| GPT hallucination in compilation | High | Prompt forbids invented facts, show sources alongside |
| 10K TPM exceeded | Medium | Sequential processing, 0.5s delays |
| Pipeline timeout | Medium | Each task still < 1800s |

---

## 11. Backward Compatibility

- All existing pages work unchanged
- All new columns are nullable (NULL = pre-upgrade articles)
- Articles without `story_id` remain standalone
- Compilation pass is optional — skip doesn't break anything
- API adds Optional fields only — old clients unaffected

---

## 12. Files to Create

| File | Purpose |
|------|---------|
| `notebooks/01b_fulltext_scraping.py` | Full-text extraction from article URLs |
| `notebooks/03b_story_matching.py` | Cross-source story grouping |
| `api/routers/stories.py` | Compiled stories API endpoints |
| `frontend/app/story/[id]/page.tsx` | Compiled story view page |

## 13. Files to Modify

| File | Changes |
|------|---------|
| `notebooks/01_bronze_ingestion.py` | Expand RSS_FEEDS to 20+ |
| `notebooks/02_silver_transformation.py` | JOIN fulltext, add columns |
| `notebooks/03_gold_aggregation.py` | Add full_text columns to MERGE |
| `notebooks/04_ai_enrichment.py` | Prompt upgrade + Pass 3 (compilation) |
| `notebooks/05_serving_projection.py` | Add compiled_stories serve table |
| `deploy_to_databricks.py` | 5→7 tasks in pipeline |
| `api/models.py` | New models: CompiledStory, SourcePerspective |
| `api/routers/articles.py` | Add story_id + other sources |
| `api/routers/home.py` | Add multi-source stories section |
| `frontend/app/article/[id]/page.tsx` | Multi-source coverage section |
| `frontend/app/page.tsx` | Multi-Source Stories section |
