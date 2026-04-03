# Smart News — Web Product, Serving Layer, and Delivery Plan

## Document Purpose

This document defines the product vision, user experience, serving architecture, functional scope, and delivery roadmap for the **Smart News** platform.

The project already produces curated news data up to the **Gold layer** in Azure Databricks. The next step is to design the **web-serving layer** and the **user-facing product** that will consume that Gold data and turn it into a usable, differentiated news experience.

This document is intended to guide implementation by engineering agents and human developers.

---

## 1. Product Vision

### 1.1 Core Idea

Smart News is an AI-assisted news aggregation and curation platform built on **Azure + Azure Databricks**.

It ingests articles from predefined sources, normalizes and enriches them in the lakehouse, applies AI-based classification and quality signals, and serves them through a web platform that helps users discover:

- important news,
- relevant technology developments,
- world events,
- social and cultural topics,
- and high-signal stories with lower hype and better credibility.

### 1.2 Product Goal

The goal is **not** to be another generic news website.

The goal is to become a **high-signal discovery platform** that:

- reduces noise,
- groups stories intelligently,
- explains why a story matters,
- highlights hype and credibility risk,
- and gradually personalizes the experience based on user behavior.

### 1.3 Product Positioning

Smart News should sit between:

- a **news aggregator**,
- an **AI-curated briefing tool**,
- and a **personalized discovery platform**.

It should feel more structured than social feeds, more intelligent than RSS readers, and more transparent than opaque recommendation engines.

---

## 2. Business and Product Objectives

## 2.1 Primary Objectives

1. **Aggregate news efficiently** from a controlled set of trusted sources.
2. **Classify and enrich** articles with AI-generated metadata.
3. **Reduce low-quality or overhyped content** using scoring and ranking logic.
4. **Serve a fast, modern web experience** for browsing and discovery.
5. **Create a foundation for personalization** using clickstream and user behavior.
6. **Build a reusable platform** that can later support mobile apps, newsletters, or premium summaries.

## 2.2 MVP Success Criteria

The MVP should achieve the following:

- Users can browse recent articles by category.
- Users can search and filter articles.
- Each article card includes useful metadata beyond title and source.
- The platform clearly surfaces AI-enriched fields such as category, summary, and quality indicators.
- The system can serve fresh content with acceptable latency.
- User events are captured for future recommendation and ranking.

## 2.3 Long-Term Objectives

Later versions can evolve into:

- personalized home feeds,
- “why this matters” daily briefings,
- cluster-based topic pages,
- alerting and monitoring for selected topics,
- premium analyst-style summaries,
- and domain-specific verticals such as AI, data engineering, startups, or geopolitics.

---

## 3. What Exists Today vs. What Comes Next

## 3.1 Current State

The project has already progressed up to the **Gold layer** in Azure Databricks.

That means raw and transformed articles are already being ingested and enriched into structured, high-quality datasets.

## 3.2 Next Major Problem to Solve

The next problem is:

> How do we serve Gold-layer intelligence through a web platform in a way that is fast, useful, intuitive, and product-ready?

This requires decisions in four areas:

1. **Serving architecture**
2. **API design**
3. **Web product design**
4. **Behavior capture and feedback loops**

---

## 4. Product Principles

The web platform should follow these principles.

### 4.1 Signal over Volume

Do not overwhelm users with undifferentiated article lists.

The system should rank, group, summarize, and annotate articles so the experience emphasizes relevance and quality rather than raw volume.

### 4.2 Explainability over Black Box

Users should understand why they are seeing a story.

Examples:

- “Trending in AI tools”
- “High credibility, low hype”
- “Related to articles you opened this week”
- “Breaking topic cluster”

### 4.3 Structured Discovery over Endless Feed

The experience should combine:

- category navigation,
- search,
- story clusters,
- and curated sections.

The product should not behave like a purely addictive infinite scroll app.

### 4.4 AI as Enrichment, Not Decoration

AI should do meaningful work:

- classify,
- summarize,
- cluster,
- score hype,
- estimate credibility,
- extract entities,
- and improve retrieval.

AI should not be added only for superficial marketing value.

### 4.5 Progressive Personalization

The platform should start with strong editorial and algorithmic defaults.

Only after enough user behavior data is collected should it intensify personalization.

---

## 5. What the Website Will Be

The website is the **product layer on top of Gold data**.

It is not a raw Databricks dashboard.
It is not a simple list of ingested RSS articles.
It is not only a chatbot interface.

It is a **consumer-facing or internal-facing intelligent news experience**.

### 5.1 Main Website Purpose

The website should help users:

- discover important stories quickly,
- browse by category,
- understand stories faster,
- evaluate signal vs. hype,
- search historical content,
- and optionally receive a more personalized experience over time.

### 5.2 What the Website Should Provide

At minimum, the website should provide:

- a homepage with curated sections,
- category pages,
- article detail pages,
- search,
- filtering,
- AI-generated summaries,
- source and credibility metadata,
- and user interaction tracking.

### 5.3 What the Website Should Not Try to Be Initially

The initial version should **not** try to be all of the following at once:

- a full social network,
- a long-form publishing platform,
- a generic chat portal with no structure,
- a mobile-first app ecosystem,
- or a fully autonomous editorial AI.

The first version should focus on **structured browsing + AI-assisted interpretation**.

---

## 6. Core User Types

### 6.1 Casual Reader

Wants a quick, clean overview of what matters today.

Needs:

- a useful homepage,
- concise summaries,
- visible categories,
- and basic trust indicators.

### 6.2 Power Reader / Analyst

Wants to search, filter, compare, and inspect the news landscape more deeply.

Needs:

- advanced filtering,
- topic exploration,
- source-level visibility,
- and trend grouping.

### 6.3 Returning User

Wants the product to adapt gradually.

Needs:

- “for you” sections,
- continuity across sessions,
- and better story ranking over time.

### 6.4 Internal Product Owner / Admin

Wants to validate the system quality.

Needs:

- content freshness,
- ingestion confidence,
- source coverage,
- AI labeling quality,
- and operational transparency.

---

## 7. Website Information Architecture

The product should be organized around a small number of clear surfaces.

## 7.1 Home Page

The homepage is the primary product surface.

### Sections the homepage should include

1. **Top Stories**
   - High-priority stories selected by ranking logic.
   - Should balance recency, quality, and importance.

2. **Category Rows**
   - AI / Tech
   - World
   - Business / Startups
   - Society / Culture
   - Data / Platforms (optional if aligned with your niche)

3. **Low Hype / High Signal Picks**
   - Stories with stronger credibility and lower hype score.

4. **Trending Topics**
   - Topic clusters instead of only individual articles.

5. **Latest Briefs**
   - Fast-scanning short summaries for recent updates.

6. **For You** (phase 2)
   - Personalized ranking based on user interactions.

## 7.2 Category Pages

Each category page should provide:

- latest stories,
- filtered lists,
- cluster groups,
- sorting options,
- and category-specific metadata.

Example categories:

- AI / Agents
- Technology
- World
- Business
- Society
- Culture / Lifestyle

## 7.3 Search Page

The search page should support:

- keyword search,
- hybrid semantic search,
- filters by category/source/date,
- and optionally topic/entity facets.

## 7.4 Article Detail Page

The article page is where Smart News adds the most value beyond simply linking out.

It should include:

- headline,
- source,
- publication date,
- original article link,
- AI summary,
- category and topic tags,
- hype and credibility indicators,
- related stories,
- and “why this matters” style context.

## 7.5 Topic / Cluster Page (phase 2)

When multiple articles refer to the same story or trend, they should be grouped into topic clusters.

A topic page should provide:

- a cluster summary,
- timeline of related articles,
- multiple source perspectives,
- key entities,
- and related categories.

---

## 8. UI and UX Direction

### 8.1 Desired Feel

The site should feel:

- modern,
- clean,
- information-dense but not cluttered,
- trustworthy,
- and intentionally calmer than social media feeds.

### 8.2 Visual Characteristics

Recommended direction:

- clean cards,
- clear typography,
- calm visual hierarchy,
- emphasis on metadata,
- restrained color system,
- visible category labels,
- credibility and hype badges,
- strong use of whitespace.

### 8.3 UX Strategy

The UX should optimize for two modes:

1. **Quick scan mode**
   - What matters right now?
   - Which stories are worth opening?

2. **Deep dive mode**
   - Show related context, clusters, summaries, and linked coverage.

### 8.4 Card Design Expectations

An article card should show more than a normal news card.

Recommended fields:

- title,
- source,
- published time,
- category,
- short summary snippet,
- hype indicator,
- credibility indicator,
- and optionally key tags or entities.

---

## 9. Gold Layer to Serving Layer: What Happens After Gold

Gold is not yet the product. Gold is the **trusted analytical output** of the pipeline.

After Gold, the platform needs a dedicated serving layer.

## 9.1 Why Gold Should Not Be Hit Directly by the Web App

Directly coupling the web app to Gold tables creates unnecessary risk in:

- latency,
- concurrency,
- schema volatility,
- operational coupling,
- and product evolution.

Instead, Smart News should introduce a **serving model** between Gold and the front-end.

## 9.2 Recommended Serving Pattern

Recommended flow:

**Sources -> Bronze -> Silver -> Gold -> Serving Projection -> API -> Web App**

This “serving projection” is a product-oriented dataset optimized for user-facing queries.

## 9.3 Serving Projection Responsibilities

The serving layer should:

- flatten the fields needed by the UI,
- precompute feed-ready shapes,
- store denormalized values for fast reads,
- expose ranking-friendly fields,
- support pagination,
- and decouple product queries from analytical tables.

## 9.4 Example Serving Tables / Views

Examples:

- `serve.article_cards`
- `serve.article_detail`
- `serve.topic_clusters`
- `serve.category_feeds`
- `serve.trending_topics`
- `serve.user_feed_candidates`

These can be materialized using Databricks jobs or SQL pipelines.

---

## 10. Recommended Azure + Databricks Serving Architecture

## 10.1 Architecture Overview

Recommended product-serving architecture:

1. **Azure Databricks**
   - Maintains Bronze / Silver / Gold
   - Produces serving projections

2. **Databricks SQL Warehouse**
   - Used for fast SQL access to serving views/tables
   - Recommended by Databricks as the query layer for warehousing workloads, with serverless warehouses recommended where available. This makes it a strong candidate for the serving query layer when product-facing reads are moderate and predictable. [Sources below in citations section]

3. **API Layer on Azure**
   - Azure Functions or Azure Container Apps
   - Handles authentication, request shaping, caching, and user events

4. **Web Frontend**
   - React / Next.js or similar
   - Consumes API endpoints, not raw Databricks tables

5. **Optional Search Layer**
   - Azure AI Search for hybrid and vector-enabled retrieval
   - Useful for semantic search, topic discovery, and related stories

## 10.2 Why This Architecture Fits This Project

This architecture separates concerns cleanly:

- Databricks remains the data and enrichment engine.
- The API becomes the product contract.
- The web app stays simple and fast.
- Search can evolve independently.
- Personalization can later use the same event pipeline.

## 10.3 SQL Warehouse Role

Databricks SQL warehouses are designed for querying and exploration of data in Azure Databricks, and Databricks recommends serverless SQL warehouses where available. That makes them a natural fit for Smart News serving queries over curated serving tables. citeturn0search1turn0search9turn0search21

---

## 11. Functional Scope of the Website

## 11.1 Required MVP Features

### Browsing
- Homepage with curated sections
- Category pages
- Latest stories
- Sorting and filtering

### Article Experience
- Article cards
- Detail page
- AI summary
- Original source link
- Related stories

### Search and Discovery
- Basic keyword search
- Date/source/category filtering
- Trending topics

### User Signals
- Click tracking
- Save/bookmark tracking
- Hide/not interested tracking
- Dwell time capture

### Platform Basics
- Responsive layout
- Fast page loads
- Pagination or infinite scroll with control
- Error handling and graceful empty states

## 11.2 Phase 2 Features

- personalized home feed,
- topic clusters,
- “why this matters” explanations,
- newsletter or digest generation,
- entity pages,
- source comparison views,
- and user preference controls.

## 11.3 Phase 3 Features

- daily AI-generated briefing,
- alerts and notifications,
- follow-topic functionality,
- premium intelligence dashboards,
- editorial quality feedback loops,
- and mobile applications.

---

## 12. AI-Enriched Data the Website Should Surface

The website should expose the value created in Gold.

Recommended fields to surface:

- `category`
- `subtopic`
- `summary`
- `entities`
- `source_name`
- `published_at`
- `hype_score`
- `credibility_score`
- `topic_cluster_id`
- `related_article_count`
- `language`
- `importance_score`
- `freshness_score`

### 12.1 Hype Score

Hype score should represent how likely an article is to be:

- exaggerated,
- clickbait-like,
- thinly sourced,
- repetitive,
- or framed more for excitement than substance.

### 12.2 Credibility Score

Credibility score should estimate trust signals such as:

- source quality,
- presence of concrete evidence,
- consistency with other reports,
- specificity,
- and signal density.

### 12.3 Important Product Rule

These scores should be treated as **signals**, not absolute truth.

The UI should avoid making overly aggressive claims like “fake” unless there is a stronger verification system.

Better labels:

- “High hype risk”
- “Lower confidence”
- “Strong source quality”
- “Needs verification”

---

## 13. Search Strategy

Search should become one of the strongest product features.

## 13.1 Search Modes

1. **Keyword search**
2. **Semantic search**
3. **Hybrid search**
4. **Facet-based filtering**

Azure AI Search supports hybrid search by running full-text and vector search together in one query and merging results with Reciprocal Rank Fusion. This is highly relevant for Smart News because users may search by exact terms, broad intent, or concept similarity. citeturn0search3turn0search11turn0search19

## 13.2 What Search Should Support

Users should be able to search for:

- topics,
- companies,
- products,
- people,
- countries,
- events,
- and themes such as “AI regulation” or “chip export restrictions”.

## 13.3 Why Search Matters Here

Search is not only a utility feature.

In this product, search is a core discovery mechanism because the system already enriches content with metadata, embeddings, and entity extraction.

---

## 14. Personalization Strategy

Personalization should be introduced progressively.

## 14.1 Initial Position

Do not start with a fully personalized black-box feed.

Instead start with:

- editorially sensible ranking,
- category browsing,
- and transparent sections.

## 14.2 Behavioral Signals to Capture

The platform should capture:

- article opens,
- dwell time,
- bookmarks,
- hides,
- category visits,
- search queries,
- and repeat source interactions.

## 14.3 Phase 2 Personalization Logic

Possible ranking inputs:

- recency,
- article importance,
- source quality,
- novelty,
- similarity to prior user interactions,
- diversity penalty,
- and hype penalty.

## 14.4 Product Rule

Personalization should improve relevance without trapping users in a narrow bubble.

That means the ranking system should preserve:

- topic diversity,
- category diversity,
- and occasional discovery content.

---

## 15. API Layer Responsibilities

The API layer is the bridge between the product and the data platform.

It should be treated as a stable contract.

## 15.1 Main Responsibilities

- Serve homepage sections
- Serve category feeds
- Serve article details
- Serve search results
- Log user events
- Apply caching
- Enforce auth if needed
- Handle personalization logic or delegate ranking decisions

## 15.2 Example Endpoint Groups

### Content
- `GET /api/home`
- `GET /api/categories`
- `GET /api/category/{slug}`
- `GET /api/article/{id}`
- `GET /api/topics/{id}`

### Search
- `GET /api/search?q=`

### User Signals
- `POST /api/events/click`
- `POST /api/events/save`
- `POST /api/events/hide`
- `POST /api/events/dwell`

### Personalization
- `GET /api/feed/for-you`

## 15.3 API Design Rule

The API should return **UI-ready payloads**, not raw warehouse-like structures.

That means it should return card-friendly and page-friendly objects.

---

## 16. Non-Functional Requirements

## 16.1 Performance

- Homepage should load quickly.
- Category pages should support pagination efficiently.
- Search should feel interactive.
- Detail pages should render summaries and related stories without noticeable lag.

## 16.2 Freshness

- New articles should appear quickly after ingestion.
- The platform should expose freshness metadata when relevant.

## 16.3 Reliability

- Serving should continue even if parts of enrichment lag.
- Partial degradation should be acceptable.
- Missing optional AI fields should not break the UI.

## 16.4 Scalability

The architecture should support growth in:

- number of sources,
- article volume,
- traffic,
- search complexity,
- and personalization workloads.

## 16.5 Security

- API secrets in Key Vault
- Principle of least privilege
- Controlled access to Databricks resources
- Optional user auth depending on product strategy

## 16.6 Observability

Track:

- ingest lag,
- serving freshness,
- API latency,
- search latency,
- failed enrichment counts,
- and event capture health.

---

## 17. Why Azure Databricks Is the Right Core for This Project

Azure Databricks is a strong fit because the Smart News platform needs:

- layered refinement of incoming data,
- scalable batch and micro-batch processing,
- structured enrichment pipelines,
- SQL serving capability,
- and future support for analytics and recommendation logic.

Databricks and Azure documentation both emphasize medallion/lakehouse approaches for incrementally improving data quality across layers. That maps directly to this project’s Bronze -> Silver -> Gold pattern. citeturn0search0turn0search8turn0search12turn0search20

---

## 18. Why Azure OpenAI and AI Search Fit This Product

Azure OpenAI Responses API supports stateful, multi-turn response workflows and consolidates capabilities that were previously split across older interfaces. This makes it suitable for article enrichment pipelines and future product-side assistant features. citeturn0search2turn0search10

Azure AI Search supports text, vector, and hybrid retrieval, which makes it a strong option for search, related stories, semantic discovery, and future RAG-style capabilities on the Smart News corpus. citeturn0search3turn0search7turn0search11turn0search19

---

## 19. Delivery Plan

## 19.1 Phase 1 — Serve the Gold Data

Objective:
Create the first usable web product from existing Gold tables.

Deliverables:
- Serving projections from Gold
- Databricks SQL warehouse access
- API layer
- Homepage
- Category page
- Article detail page
- Basic search

Outcome:
Users can browse and consume enriched news.

## 19.2 Phase 2 — Add Product Intelligence

Objective:
Move from static serving to intelligent discovery.

Deliverables:
- Topic clustering
- Related story logic
- Trending sections
- Better search
- Quality-focused ranking

Outcome:
The platform becomes distinctly smarter than a normal aggregator.

## 19.3 Phase 3 — Add User Intelligence

Objective:
Make the experience adapt to behavior.

Deliverables:
- Event pipeline
- User profile generation
- Personalized ranking
- Saved content
- “For you” sections

Outcome:
The platform becomes habit-forming without losing transparency.

## 19.4 Phase 4 — Add Agentic Features

Objective:
Expose the AI layer more directly to users.

Deliverables:
- daily AI briefings,
- “ask about this topic” assistant,
- topic explainers,
- and smart monitoring/alerts.

Outcome:
The product evolves from a curated site into an intelligent news companion.

---

## 20. Recommended Immediate Next Steps

1. Define the **serving contract** from Gold to the web product.
2. Design the **serve schema** for article cards, detail pages, and category feeds.
3. Build the first **Databricks SQL views/materialized tables** for serving.
4. Create a thin **API layer** in Azure.
5. Build the first **homepage + category + article page**.
6. Add **event tracking** from day one.
7. Introduce **search** as early as possible.
8. Add **topic clustering and personalization** only after the structured browsing experience works well.

---

## 21. Final Product Statement

Smart News should become a product where:

- Azure Databricks is the intelligence and refinement engine,
- Azure services provide secure serving and application infrastructure,
- AI adds structured meaning and quality signals,
- and the website turns that data into a clear, elegant, high-signal user experience.

The Gold layer gives the platform intelligence.
The serving layer gives it performance.
The website gives it product value.

Together, these layers turn Smart News from a data pipeline into a real application.
