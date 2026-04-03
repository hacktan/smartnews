# SmartNews — Product Goals & Competitive Strategy

This document defines the goals, principles, competitive positioning, and phased roadmap for SmartNews.
It must be consulted at every phase of development to prevent scope drift.

---

## Core Mission

SmartNews is a **high-signal news discovery platform with radical transparency**.

It is NOT:
- a generic RSS reader
- a social feed with infinite scroll
- a simple news aggregator
- a chatbot interface without structure

It IS:
- an AI-enriched, curated browsing experience with **visible, explainable scoring**
- a platform that reduces noise and surfaces signal — and **proves it with data**
- a structured discovery tool where every ranking decision is transparent
- a foundation for progressive personalization that **preserves topic diversity**
- a media literacy tool that helps readers **understand their own information diet**

---

## Competitive Positioning

### The Market Gap We Fill

After analyzing Google News, Apple News, SmartNews (app), Artifact (dead), Feedly, Ground News, Flipboard, and Perplexity Discover — **no platform combines all three of these**:

1. **Quantitative scoring with full transparency** — hype, credibility, importance scores visible to users (Ground News does bias but not hype/credibility; no one else exposes numerical trust signals)
2. **Score-based filtering and navigation** — let users set trust thresholds ("show me only credibility > 0.7 AND hype < 0.3"); no competitor offers this
3. **AI enrichment that's visible, not hidden** — "Why It Matters", de-hyped headlines, entity extraction, all surfaced in the UI (most platforms hide their AI behind personalization)

### What Makes Us Different

| Capability | Google News | Apple News | Ground News | Feedly | Perplexity | **SmartNews (Ours)** |
|---|---|---|---|---|---|---|
| AI-generated hype score | -- | -- | -- | -- | -- | **Yes** |
| Credibility scoring | -- | -- | Bias only | -- | -- | **Yes** |
| Score-based user filtering | -- | -- | -- | -- | -- | **Yes** |
| "Why It Matters" context | -- | -- | -- | -- | -- | **Yes** |
| De-hyped headline rewriting | -- | -- | -- | -- | -- | **Yes** |
| Source trust leaderboard | -- | -- | Partial | -- | -- | **Yes** |
| Reading habit bias dashboard | -- | -- | Yes | -- | -- | **Planned** |
| Multi-source story clustering | Yes | -- | Yes | -- | -- | **Planned** |
| Entity-centric navigation | Partial | -- | -- | -- | -- | **Planned** |
| AI daily briefings (score-aware) | -- | -- | -- | -- | Partial | **Planned** |

### Our Moat (Hard to Copy)

1. **End-to-end scoring pipeline** — Bronze → Silver → Gold → Serve → API → Frontend, every article scored on 3 axes before it reaches the user
2. **Transparency-first design** — scores are UI features, not hidden backend metadata
3. **No filter bubble by design** — diversity-preserving ranking from day one (P5 principle)
4. **Score evolution tracking** — we can show how a story's hype/credibility changes over time (novel, no competitor does this)

---

## Layered Goals

### Layer 0 — Data Foundation (COMPLETE)
- [x] Ingest RSS feeds into Bronze Delta table (MERGE on entry_id)
- [x] Clean, categorize, and enrich articles in Silver
- [x] Produce daily Gold aggregations with partition overwrite
- [x] Pipeline runs via Databricks Job (every 4 hours)
- [x] Notebooks stored in Databricks workspace
- [x] Cost-optimized: 1 shared job cluster, SPOT_WITH_FALLBACK_AZURE, Standard_D4s_v3

### Layer 1 — AI Enrichment (COMPLETE)
- [x] Generate AI summaries per article (Azure OpenAI gpt-4o-mini)
- [x] Compute `hype_score` (0.0-1.0): likelihood of exaggeration or clickbait
- [x] Compute `credibility_score` (0.0-1.0): source quality + specificity signals
- [x] Compute `importance_score` (0.0-1.0): relevance and impact estimate
- [x] Extract named entities (people, companies, places, products)
- [x] Assign `subtopic` within category
- [x] Generate `why_it_matters` contextual explanation
- [x] Store enriched fields in `gold.news_articles` via MERGE

### Layer 2 — Serving Projection (COMPLETE)
- [x] Create `serve` schema in Unity Catalog
- [x] Build `serve.article_cards` — flat, UI-ready, pageable
- [x] Build `serve.category_feeds` — per-category, sorted, pageable
- [x] Build `serve.trending_topics` — cluster-level aggregation
- [x] Build `serve.article_detail` — full enriched article object
- [x] TF-IDF cosine similarity for related stories (Spark MLlib, 8192 features)
- [x] Refresh serving tables on every pipeline run

### Layer 3 — API Layer (COMPLETE)
- [x] Deploy FastAPI on Azure Container Apps
- [x] `GET /api/home` — homepage sections
- [x] `GET /api/categories` — category list
- [x] `GET /api/category/{slug}` — paginated category feed
- [x] `GET /api/article/{id}` — article detail with AI fields
- [x] `GET /api/search?q=` — keyword + filter search
- [x] API returns UI-ready payloads, not raw warehouse structures
- [x] API uses in-memory caching (cachetools, 3-min TTL)
- [x] Auto-reconnect on stale Databricks connection (SQL Warehouse idle/restart)

### Layer 4 — Web Frontend (COMPLETE)
- [x] Next.js 16 application (App Router, TypeScript, Tailwind CSS)
- [x] Homepage with: Top Stories, Low Hype Picks, Trending Topics, Latest Briefs
- [x] Category pages with pagination
- [x] Article detail page with AI summary, score dashboard, entity cloud
- [x] "Why It Matters" amber contextual banner on article detail
- [x] Basic keyword search with date/source/category filters
- [x] Article cards showing: title, source, time, category, summary snippet, score badges
- [x] Responsive layout (mobile + desktop)
- [x] Deployed to Azure Container Apps (standalone Docker, Next.js 16)
- [x] CI/CD via GitHub Actions (auto-deploy on push to `frontend/**`)

---

### Layer 5 — Product Intelligence (Phase 2 — IN PROGRESS)

> **Theme**: Make the intelligence layer deeper, broader, and more useful. Unlock embeddings as the foundation for everything that follows.

#### 5A — Embedding Foundation ✅ COMPLETE
- [x] TF-IDF related stories (HashingTF + IDF + StopWordsRemover, 8192 features)
- [x] Add `text-embedding-3-small` embedding generation to `04_ai_enrichment.py` (separate incremental pass, WHERE embedding IS NULL)
- [x] Store embeddings in Gold table as STRING column (JSON array, 1536-dim)
- [x] Upgrade related stories from TF-IDF to embedding cosine similarity (TF-IDF fallback when < 5 embeddings)

#### 5B — Score-Based Smart Filters ✅ COMPLETE
- [x] API: `GET /api/search` accepts `min_credibility`, `max_hype`, `min_importance` params
- [x] Frontend: preset filter buttons — "Verified Signal" (cred > 0.7, hype < 0.3), "Breaking & Bold" (imp > 0.7), "Deep Analysis" (cred > 0.7, imp > 0.5), "Low Hype" (hype < 0.25)
- [ ] Frontend: advanced filter sliders for manual threshold selection

#### 5C — De-Hyped Headlines ✅ COMPLETE
- [x] When `hype_score > 0.6`, generate alternative factual headline in AI enrichment (max 15 words)
- [x] Store as `dehyped_title` in Gold → Serve (article_cards + article_detail) → API (ArticleDetail model)
- [x] Frontend: green "De-Hyped" callout banner on article detail page when hype > 0.6
- [ ] Frontend: show toggle "Original / De-hyped" on high-hype article cards (homepage/search)
- [ ] *Artifact (Instagram founders' app) had this — they shut down, gap is wide open*

#### 5D — Source Trust Leaderboard ✅ COMPLETE
- [x] API: `GET /api/sources/leaderboard` — aggregate credibility + hype + importance per source
- [x] Frontend: `/sources` page showing source credibility rankings
- [ ] Add trend arrows (requires historical snapshots)
- [ ] Leverages existing `gold.daily_source_summary` table

#### 5E — Story Clustering ✅ COMPLETE
- [x] "Why this matters" contextual explanations
- [x] KMeans clustering on TF-IDF vectors in `05_serving_projection.py` (k=max(2,min(12,n//5)), seed=42)
- [x] New serve table: `serve.story_clusters` — cluster_id, label, article_count, top_entry_ids, top_categories, avg scores
- [x] `cluster_id INT` column added to `serve.article_cards` and `serve.article_detail`
- [x] API: `GET /api/clusters` (list, ordered by avg_importance) + `GET /api/clusters/{cluster_id}` (detail with articles)
- [x] Frontend: "Story Clusters" section on homepage (top 6) + `/clusters/{id}` detail page
- [ ] Multi-source story pages: same event, different angles, compared scores *(stretch goal, requires embedding upgrade)*
- [ ] Trending topics section upgraded with cluster summaries

#### 5F — Entity-Centric Navigation ✅ COMPLETE
- [x] New serve table: `serve.entity_index` — entity → article mappings with scores (partitioned by entity_type)
- [x] API: `GET /api/entities?limit=N` (top entities) + `GET /api/entity/{name}` (all articles mentioning entity)
- [x] Frontend: clickable entity chips in article detail → `/entity/{name}` detail page with score dashboard
- [ ] Entity score trends over time (avg hype/credibility per entity per week) *(stretch goal)*

---

### Layer 6 — Media Literacy & Transparency (Phase 3)

> **Theme**: Turn SmartNews into a tool that helps readers understand media, not just consume it. This is our strongest differentiator vs. all competitors.

#### 6A — Signal Dashboard (Personal Reading Analytics)
- [ ] Track per-session reading patterns (already have click events)
- [ ] API: `GET /api/me/dashboard` — avg hype of clicked articles, credibility distribution, category diversity index
- [ ] Frontend: `/dashboard` page with charts — "Your reading profile this week"
- [ ] Nudges: "You read 80% high-hype articles — here are 5 high-credibility alternatives"

#### 6B - Hype Decay Tracker COMPLETE (v2)
- [x] Store daily score snapshots in `serve.hype_snapshots` with daily upsert (`topic+category+snapshot_date`)
- [x] API: `GET /api/topics/{topic}/history?days=N` returns ordered points + `insufficient_data` + latest + 7d deltas
- [x] Frontend: `/topic/[name]` trend page with metric cards and fallback when data is insufficient
- [x] Cluster integration: `/clusters/[id]` includes Topic Trend panel linked to `/topic/[name]`

#### 6C — Blind Spot Alerts
- [ ] Detect topics/entities covered by only 1 source in our feed
- [ ] API: `GET /api/insights/blind-spots` — stories with single-source coverage
- [ ] Frontend: "Blind Spot" section on homepage or insights page
- [ ] *Inspired by Ground News, but built on entity extraction + source tracking rather than political bias*

#### 6D — Credibility Breakdown
- [ ] Split `credibility_score` into sub-signals: source_reputation, specificity, attribution_quality, evidence_strength
- [ ] Show breakdown on article detail page as radar chart
- [ ] Add to AI enrichment prompt (4 sub-fields instead of 1 aggregate)

---

### Layer 7 — Agentic Features & Personalization (Phase 4)

> **Theme**: Move from browsing to proactive intelligence. The platform starts working *for* the user.

#### 7A — AI Briefing (Score-Aware Daily Digest) ✅ COMPLETE
- [x] API: `GET /api/briefing/daily` — AI-synthesized 5-bullet daily digest
- [x] Weighted by importance (> 0.4), filtered for low hype (< 0.7), top 7 articles
- [x] Frontend: `/briefing` page — "Today's Signal" with markdown bullet rendering
- [x] Navbar "Briefing" link added
- [x] Generated in 05_serving_projection.py → stored in serve.daily_briefing (updates every pipeline run)
- [ ] Optional: personalized briefing based on reading history *(stretch goal)*

#### 7B — Narrative Tracker (Story Arcs)
- [ ] Group articles into temporal narrative arcs (same story evolving over days)
- [ ] Timeline view: "Day 1: Announcement → Day 3: Expert reaction → Day 5: First reviews"
- [ ] Each node shows score shifts (hype went up/down, credibility changed)
- [ ] *Goes beyond "related stories" into story evolution tracking*

#### 7C — Progressive Personalization
- [ ] Event pipeline → user profile generation from click/dwell/save events
- [ ] `GET /api/feed/for-you` personalized feed
- [ ] Saved/bookmarked articles per user
- [ ] Category preference learning
- [ ] Ranking inputs: recency + importance + novelty + diversity
- [ ] **Must preserve topic diversity — no filter bubbles** (P5)

#### 7D — Smart Alerts & Monitoring
- [ ] "Ask about this topic" conversational assistant (Azure OpenAI)
- [ ] Topic monitoring and alerts (email/push when entity gets new coverage)
- [ ] Smart digests / newsletters (weekly roundup)

---

### Layer 8 — Scale & Multi-Source Foundation (Phase 5)

> **Theme**: Expand from 3 RSS feeds to a real multi-source platform. This layer is the prerequisite for the Verification Engine.

#### 8A — Source Expansion
- [ ] Add 20+ RSS/API sources across tech, business, science, politics
- [ ] Political lean detection per source (left/center/right)
- [ ] International sources with multi-language support

#### 8B — Full-Text Ingestion
- [ ] Scrape full article text from source URLs (trafilatura / newspaper3k)
- [ ] Store full text in `gold.article_fulltext` (separate from summary)
- [ ] Extract structured claims from full text (LLM-powered claim extraction)
- [ ] *This enables cross-source verification — RSS summaries are not enough*

#### 8C — Semantic Search
- [ ] Azure AI Search integration with hybrid retrieval (keyword + embedding)
- [ ] Search results ranked by relevance + trust scores
- [ ] "More like this" semantic search from any article

#### 8D — iOS App
- [ ] Native iOS app consuming the same API
- [ ] Push notifications for alerts and blind spot detection
- [ ] Offline reading support
- [ ] Widget for daily briefing

#### 8E — API Platform
- [ ] Public API for researchers and developers
- [ ] Webhook subscriptions for topic alerts
- [ ] Bulk data export for media studies

---

### Layer 9 — Verification Engine (Phase 6)

> **Theme**: The ultimate differentiator. SmartNews becomes the platform that doesn't just aggregate news — it **verifies** it. Multiple sources covering the same story are cross-referenced, claims are extracted, contradictions are surfaced, and scientific/academic backing is linked where available. No news platform in the world does this end-to-end with full transparency.

#### 9A — Cross-Source Claim Extraction
- [ ] For each story cluster (Layer 5E), extract factual claims from every source's full text
- [ ] Structured claim format: `{"claim": "...", "source": "...", "confidence": 0.0-1.0, "evidence_type": "statistic|quote|assertion|reference"}`
- [ ] Store in `gold.story_claims` table linked to story cluster ID
- [ ] LLM-powered: Azure OpenAI parses each source's version and extracts discrete claims

#### 9B — Claim Consensus Analysis
- [ ] Compare claims across sources within the same story cluster
- [ ] Detect: **confirmed** (multiple sources agree), **disputed** (sources contradict), **exclusive** (only one source reports)
- [ ] Generate `consensus_score` per claim (0.0 = single unverified source, 1.0 = all sources agree)
- [ ] Surface contradictions: "BBC says X, but NYT says Y — here's what each cites"
- [ ] Serve table: `serve.story_verification` — per-cluster verification summary

#### 9C — Scientific & Academic Backing
- [ ] Integrate with academic APIs: Semantic Scholar, PubMed, arXiv
- [ ] When a claim references research/data, attempt to find the original paper
- [ ] Add `academic_references` field: links to papers that support or contradict the claim
- [ ] AI-generated "Evidence Check": "This claim about [topic] is supported by [paper title, journal, year]" or "No academic backing found for this claim"
- [ ] Frontend: "Research Backing" section on article detail — green checkmarks for backed claims, amber warnings for unverified

#### 9D — Refined Story Synthesis
- [ ] For each story cluster, generate a **verified synthesis** — a single, refined narrative that:
  - Uses facts confirmed across multiple sources
  - Flags disputed claims with both sides cited
  - Links to academic papers where applicable
  - Removes sensationalized language (leverages de-hyped headline tech from 5C)
  - Clearly marks what is fact vs. opinion vs. speculation
- [ ] API: `GET /api/story/{cluster_id}/verified` — the "truth layer" for a story
- [ ] Frontend: `/story/{id}` — verified story page with claim-by-claim breakdown
- [ ] Each claim shows: which sources confirm it, which dispute it, and any academic backing

#### 9E — Misinformation Detection
- [ ] Flag articles with claims that contradict well-sourced consensus
- [ ] Show warning banner: "This article contains claims disputed by 4 other sources"
- [ ] Never label as "fake" — instead show the evidence and let the reader decide (P6 principle)
- [ ] Track misinformation patterns per source over time → feeds into Source Trust Leaderboard (5D)

#### Why This Changes Everything
```
Traditional news platform:  Source → Article → Reader (trust the source)
SmartNews with Verification: Sources → Claims → Cross-reference → Evidence → Verified Synthesis → Reader (trust the evidence)
```
- Google News groups sources but doesn't verify claims
- Ground News shows bias but doesn't extract and compare claims
- Perplexity synthesizes but doesn't do multi-source claim verification with academic backing
- **No platform combines: claim extraction + cross-source consensus + academic backing + transparent scoring**

---

## Product Principles (Non-Negotiable)

### P1 — Signal over Volume
Never show raw, undifferentiated article lists as the primary experience.
Always rank, group, or annotate.

### P2 — Explainability over Black Box
Every article placement must have a visible reason.
Examples: "Trending in AI", "High credibility", "Low hype pick"

### P3 — Structured Discovery over Endless Feed
The experience must combine category navigation + search + curated sections.
It must NOT behave like an addictive infinite scroll app.

### P4 — AI as Enrichment, Not Decoration
AI must do meaningful work: classify, summarize, score, cluster, extract, de-hype.
AI must not be added for superficial marketing value.

### P5 — Progressive Personalization
Start with strong editorial defaults.
Personalize only after collecting sufficient behavioral signals.
Personalization must preserve topic diversity — no filter bubbles.

### P6 — Scores are Signals, Not Verdicts
Hype and credibility scores are indicators, not absolute truth.
UI must use soft labels: "High hype risk", "Strong source quality", "Needs verification"
Never label content as "fake" without a verified system.

### P7 — Gold Must Not Be Hit Directly
The web app must never query Gold tables directly.
All product queries go through Serving tables -> API -> Frontend.

### P8 — Radical Transparency (NEW)
Every score, ranking, and recommendation must be explainable to the user.
Source quality metrics must be publicly visible, not hidden.
Users should understand *why* they see what they see.

### P9 — Media Literacy as Feature (NEW)
The platform actively helps users understand media quality and their own biases.
Reading habit analytics, blind spot detection, and credibility breakdowns are core features, not add-ons.

### P10 — Verification Through Evidence, Not Authority (NEW)
The platform verifies claims by cross-referencing multiple sources and linking to academic research.
Never declare something "true" or "fake" by authority — show the evidence, the consensus, and the contradictions.
Let the reader decide, armed with full transparency.

---

## Architecture Invariants

```
RSS/API Sources (20+ publishers)
  -> Bronze (raw, deduplicated)
  -> Silver (cleaned, categorized)
  -> Gold (enriched with AI scores, embeddings, full text, claims)
  -> Verification (cross-source claim consensus, academic backing)
  -> Serve (UI-ready projections, clusters, entity index, verified stories)
  -> API (contract layer, score-based filtering, verification endpoints)
  -> Web / iOS (product surfaces, dashboards, briefings, verified story pages)
```

- Databricks = intelligence, enrichment, and verification engine
- API = stable product contract
- Frontend = fast, simple consumer of API
- Each layer must be independently evolvable
- Embeddings are the foundation for search, clustering, and similarity
- Verification Engine is the ultimate differentiator — built on multi-source evidence, not opinion

---

## MVP Success Criteria (ACHIEVED)

The MVP (Layer 1-4 complete) is successful when:

1. [x] Users can browse recent articles by category
2. [x] Each article card shows AI-enriched metadata (not just title + source)
3. [x] Hype and credibility badges are visible and meaningful
4. [x] Homepage surfaces at least 3 curated sections
5. [x] Search works with at minimum keyword + category filter
6. [x] Article detail page shows AI summary and related articles
7. [x] User click and dwell events are being captured
8. [x] Content is refreshed at least every 4 hours
9. [x] Page loads are fast (< 2s for homepage)
10. [x] Missing AI fields do not break the UI

## Phase 2 Success Criteria (Layer 5 — In Progress)

Phase 2 is successful when:

1. [ ] Score-based filtering is live (users can filter by credibility/hype thresholds)
2. [ ] De-hyped headlines appear on high-hype articles
3. [ ] Source trust leaderboard is visible at `/sources`
4. [ ] Related stories use embedding similarity (not just TF-IDF)
5. [ ] At least one story cluster groups 3+ articles about the same event
6. [ ] Entity pages show article timelines with score trends

## Phase 3 Success Criteria (Layer 6)

Phase 3 is successful when:

1. [x] Hype Decay Tracker is live (`/topic/[name]` + cluster trend panel + history API)
2. [ ] Signal Dashboard shows users their reading patterns
3. [ ] Blind spot alerts surface under-covered stories
4. [ ] Credibility breakdown shows sub-signals (not just aggregate score)
5. [ ] At least 100 users have viewed their dashboard

---

## Phase 4 Success Criteria (Layers 8-9 — Verification Engine)

Phase 4 is successful when:

1. [ ] 10+ sources are ingested with full-text scraping
2. [ ] Story clusters contain articles from 3+ different sources
3. [ ] Claims are extracted and cross-referenced across sources within clusters
4. [ ] At least 1 academic paper is linked per 10 story clusters
5. [ ] Verified story synthesis page shows claim-by-claim breakdown with consensus scores
6. [ ] Misinformation warnings appear on articles with disputed claims (without labeling "fake")

---

## What This Product Must Never Become

- A generic news website without differentiation
- A system where AI fields are present but invisible to users
- A fully personalized black-box feed from day one
- A product that labels content as "fake" without verification
- A pipeline that serves Gold data directly to users without a serving layer
- A system where the web app is tightly coupled to Databricks schema changes
- A platform that hides its scoring methodology from users
- An addictive infinite-scroll app optimized for engagement over understanding
- A fact-checker that declares truth by authority instead of showing evidence

---

## Implementation Priority (Quick Wins First)

Based on effort vs. differentiation analysis:

### Phase 2 — Quick Wins (Layer 5)
| Priority | Feature | Effort | Differentiation |
|----------|---------|--------|-----------------|
| 1 | Score-Based Smart Filters (5B) | Small | High — no competitor |
| 2 | Source Trust Leaderboard (5D) | Small | Very High — radical transparency |
| 3 | De-Hyped Headlines (5C) | Small | Very High — Artifact's gap |
| 4 | Embedding Foundation (5A) | Small | Unlocks everything below |
| 5 | Entity Timeline (5F) | Medium | High — entity score trends |
| 6 | Story Clustering (5E) | Medium | High — multi-source grouping |

### Phase 3 — Media Literacy (Layer 6)
| Priority | Feature | Effort | Differentiation |
|----------|---------|--------|-----------------|
| 7 | Signal Dashboard (6A) | Medium | Very High — no competitor |
| 8 | Blind Spot Alerts (6C) | Medium | High — coverage gaps |
| 9 | Credibility Breakdown (6D) | Medium | High — trust decomposition |

### Phase 4 — Intelligence & Personalization (Layer 7)
| Priority | Feature | Effort | Differentiation |
|----------|---------|--------|-----------------|
| 10 | AI Briefing (7A) | Medium | High — score-aware digests |
| 11 | Narrative Tracker (7B) | Large | Very High — story evolution |
| 12 | For-You Feed (7C) | Large | Medium — many competitors have this |

### Phase 5-6 — Scale & Verification Engine (Layers 8-9)
| Priority | Feature | Effort | Differentiation |
|----------|---------|--------|-----------------|
| 13 | Source Expansion + Full-Text (8A+8B) | Large | Prerequisite for verification |
| 14 | Cross-Source Claim Extraction (9A) | Large | Very High — no competitor |
| 15 | Claim Consensus Analysis (9B) | Large | Game-changing — evidence-based trust |
| 16 | Academic Backing Integration (9C) | Large | Unprecedented — science-linked news |
| 17 | Verified Story Synthesis (9D) | Very Large | **Ultimate differentiator** |

## Current Execution Plan (High Mode - Next 10 Days)

### P0 - 6B v2 Production Closure (Days 1-2)
- [ ] Deploy latest API/frontend changes and verify both workflows are green.
- [ ] Run Databricks pipeline twice on different days to move topic history out of `insufficient_data` mode.
- [ ] Smoke test `/api/topics/{topic}/history`, `/topic/[name]`, `/clusters/[id]`.

### P1 - Embedding Blocker Removal (Day 3)
- [ ] Create Azure OpenAI deployment: `text-embedding-3-small`.
- [ ] Trigger pipeline and validate embedding backfill in `gold.news_articles`.
- [ ] Confirm serving uses embedding similarity path (not TF-IDF fallback) when enough vectors exist.

### P2 - Quick UX Win (Days 4-5)
- [ ] Implement `Original / De-hyped` card toggle on homepage and search (5C remaining).
- [ ] Ensure no regression on article cards and detail page de-hyped behavior.

### P3 - Trust Transparency Upgrade (Days 6-8)
- [ ] Ship 6D MVP: credibility sub-signals in enrichment + API + article detail visualization.
- [ ] Validate schema, backward compatibility, and fallback behavior when sub-signals are missing.

### P4 - Next Major Scope Freeze (Days 9-10)
- [ ] Finalize 7B Narrative Tracker MVP spec (data model + endpoint contract + UI skeleton).
- [ ] Convert spec to decision-complete backlog items for direct implementation.

### Tracking Metrics
- Trend usage: topic trend page views and cluster trend panel click-through rate.
- Reliability: pipeline success rate and API p95 latency on topic history endpoint.
- Data quality: ratio of topics with 2+ qualified snapshots (`article_count >= 2`).

### The End-State Vision
```
Reader opens SmartNews → sees a story covered by 5 sources →
clicks "Verified View" → sees:
  - 12 claims extracted across all sources
  - 8 confirmed by multiple sources (green)
  - 2 disputed between sources (amber, both sides shown)
  - 2 exclusive to single source (gray, unverified)
  - 3 claims linked to academic papers
  - AI-generated verified synthesis at the top
  - No "fake" labels — just evidence and consensus
```




