"""
Pydantic response models for all SmartNews API endpoints.

These models define the exact shapes returned to the frontend.
They map directly to columns in the DuckDB serve.* tables.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Article Card — used in homepage, category feeds, search results
# ---------------------------------------------------------------------------

class ArticleCard(BaseModel):
    entry_id: str
    title: str
    source_name: str
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    summary_snippet: Optional[str] = None
    hype_score: Optional[float] = None
    credibility_score: Optional[float] = None
    importance_score: Optional[float] = None
    link: Optional[str] = None
    publish_date: Optional[str] = None
    image_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Article Detail — full enriched article object
# ---------------------------------------------------------------------------

class ArticleDetail(BaseModel):
    entry_id: str
    title: str
    dehyped_title: Optional[str] = None
    source_name: Optional[str] = None
    published_at: Optional[datetime] = None
    category: Optional[str] = None
    link: Optional[str] = None
    clean_summary: Optional[str] = None
    ai_summary: Optional[str] = None
    why_it_matters: Optional[str] = None
    hype_score: Optional[float] = None
    credibility_score: Optional[float] = None
    importance_score: Optional[float] = None
    freshness_score: Optional[float] = None
    entities: Optional[str] = None      # JSON string: [{name, type}]
    subtopic: Optional[str] = None
    language: Optional[str] = None
    word_count: Optional[int] = None
    estimated_read_time_min: Optional[int] = None
    image_url: Optional[str] = None
    related_articles: list["ArticleCard"] = []


# ---------------------------------------------------------------------------
# Category Feed item — slightly slimmer than full detail
# ---------------------------------------------------------------------------

class CategoryFeedItem(BaseModel):
    entry_id: str
    category: str
    published_at: Optional[datetime] = None
    importance_score: Optional[float] = None
    hype_score: Optional[float] = None
    credibility_score: Optional[float] = None
    title: str
    summary_snippet: Optional[str] = None
    source_name: Optional[str] = None
    image_url: Optional[str] = None


# ---------------------------------------------------------------------------
# Trending Topic
# ---------------------------------------------------------------------------

class TrendingTopic(BaseModel):
    topic: str
    article_count: int
    top_source: Optional[str] = None
    latest_at: Optional[datetime] = None
    category: Optional[str] = None


# ---------------------------------------------------------------------------
# Home endpoint sections
# ---------------------------------------------------------------------------

class HomeResponse(BaseModel):
    top_stories: list[ArticleCard]
    low_hype_picks: list[ArticleCard]
    trending_topics: list[TrendingTopic]
    latest_briefs: list[ArticleCard]
    category_rows: dict[str, list[ArticleCard]] = {}


# ---------------------------------------------------------------------------
# Category endpoints
# ---------------------------------------------------------------------------

class CategoryMeta(BaseModel):
    slug: str
    label: str
    article_count: int


class CategoriesResponse(BaseModel):
    categories: list[CategoryMeta]


class CategoryFeedResponse(BaseModel):
    category: str
    page: int
    page_size: int
    total: int
    items: list[CategoryFeedItem]


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

class SearchResponse(BaseModel):
    query: str
    total: int
    items: list[ArticleCard]


# ---------------------------------------------------------------------------
# Event tracking (POST bodies)
# ---------------------------------------------------------------------------

class ClickEvent(BaseModel):
    entry_id: str
    session_id: Optional[str] = None
    source: Optional[str] = None        # "home", "category", "search"


class SaveEvent(BaseModel):
    entry_id: str
    session_id: Optional[str] = None


class HideEvent(BaseModel):
    entry_id: str
    session_id: Optional[str] = None
    reason: Optional[str] = None        # "not_interested", "already_read", etc.


class DwellEvent(BaseModel):
    entry_id: str
    session_id: Optional[str] = None
    seconds: int


class EventResponse(BaseModel):
    status: str = "ok"


# ---------------------------------------------------------------------------
# Story Clusters
# ---------------------------------------------------------------------------

class StoryCluster(BaseModel):
    cluster_id: int
    label: Optional[str] = None
    article_count: int
    top_entry_ids: Optional[str] = None   # comma-separated
    top_categories: Optional[str] = None
    avg_importance: Optional[float] = None
    avg_credibility: Optional[float] = None
    avg_hype: Optional[float] = None


class StoryClusterDetail(StoryCluster):
    primary_topic: Optional[str] = None
    articles: list["ArticleCard"] = []


# ---------------------------------------------------------------------------
# Source Leaderboard
# ---------------------------------------------------------------------------

class SourceLeaderboardItem(BaseModel):
    source_name: str
    article_count: int
    avg_credibility: Optional[float] = None
    avg_hype: Optional[float] = None
    avg_importance: Optional[float] = None


class SourceLeaderboardResponse(BaseModel):
    sources: list[SourceLeaderboardItem]


# ---------------------------------------------------------------------------
# Entity Navigation
# ---------------------------------------------------------------------------

class EntityArticle(BaseModel):
    entry_id: str
    title: str
    source_name: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None
    hype_score: Optional[float] = None
    credibility_score: Optional[float] = None
    importance_score: Optional[float] = None


class EntityResponse(BaseModel):
    entity_name: str
    entity_type: Optional[str] = None
    article_count: int
    avg_hype: Optional[float] = None
    avg_credibility: Optional[float] = None
    avg_importance: Optional[float] = None
    articles: list[EntityArticle] = []


class EntitySummary(BaseModel):
    entity_name: str
    entity_type: Optional[str] = None
    article_count: int
    avg_credibility: Optional[float] = None
    avg_hype: Optional[float] = None


class TopEntitiesResponse(BaseModel):
    entities: list[EntitySummary]


# ---------------------------------------------------------------------------
# Blind Spot Alerts (6C)
# ---------------------------------------------------------------------------

class BlindSpotItem(BaseModel):
    entity_name: str
    entity_type: Optional[str] = None
    entry_id: str
    title: str
    source_name: Optional[str] = None
    category: Optional[str] = None
    published_at: Optional[datetime] = None
    importance_score: Optional[float] = None
    hype_score: Optional[float] = None
    credibility_score: Optional[float] = None


class BlindSpotsResponse(BaseModel):
    items: list[BlindSpotItem]


# ---------------------------------------------------------------------------
# Hype Decay Tracker (6B)
# ---------------------------------------------------------------------------

class TopicHistoryPoint(BaseModel):
    snapshot_date: str
    article_count: int
    avg_hype: Optional[float] = None
    avg_credibility: Optional[float] = None
    avg_importance: Optional[float] = None


class TopicHistoryResponse(BaseModel):
    topic: str
    days: int
    insufficient_data: bool
    latest_hype: Optional[float] = None
    latest_credibility: Optional[float] = None
    delta_hype_7d: Optional[float] = None
    delta_credibility_7d: Optional[float] = None
    points: list[TopicHistoryPoint]


# ---------------------------------------------------------------------------
# Narrative Tracker (7B)
# ---------------------------------------------------------------------------

class NarrativeArc(BaseModel):
    arc_id: str
    subtopic: str
    category: Optional[str] = None
    article_count: int
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    span_days: Optional[int] = None
    hype_start: Optional[float] = None
    hype_end: Optional[float] = None
    hype_trend: Optional[float] = None          # positive = escalating, negative = cooling
    avg_importance: Optional[float] = None
    avg_hype: Optional[float] = None
    avg_credibility: Optional[float] = None
    latest_title: Optional[str] = None


class NarrativeDetail(NarrativeArc):
    entry_ids: list[str] = []
    titles: list[str] = []
    articles: list["ArticleCard"] = []


class NarrativesResponse(BaseModel):
    items: list[NarrativeArc]
    total: int


# ---------------------------------------------------------------------------
# Compiled Stories (Layer 8 — AI multi-source synthesis)
# ---------------------------------------------------------------------------

class CompiledStory(BaseModel):
    story_id: str
    compiled_title: Optional[str] = None
    compiled_summary: Optional[str] = None
    source_count: Optional[int] = None
    sources_used: Optional[str] = None        # JSON list of source names
    category: Optional[str] = None
    first_published: Optional[datetime] = None
    last_published: Optional[datetime] = None
    compiled_at: Optional[datetime] = None
    entry_ids: Optional[str] = None           # JSON list of article entry_ids


class CompiledStoryDetail(CompiledStory):
    compiled_body: Optional[str] = None
    key_claims: Optional[str] = None          # JSON
    consensus_points: Optional[str] = None    # JSON
    divergence_points: Optional[str] = None   # JSON
    source_articles: list["ArticleCard"] = []


class CompiledStoriesResponse(BaseModel):
    items: list[CompiledStory]
    total: int


# ---------------------------------------------------------------------------
# Story Claim Verification
# ---------------------------------------------------------------------------

class StoryClaim(BaseModel):
    story_id: str
    claim_group_id: str
    claim_text: str
    claim_normalized: Optional[str] = None
    verdict: str
    confidence: Optional[float] = None
    confirm_count: Optional[int] = None
    dispute_count: Optional[int] = None
    sources_confirming: Optional[str] = None   # JSON list
    sources_disputing: Optional[str] = None    # JSON list
    entry_ids: Optional[str] = None            # JSON list


class StoryClaimsResponse(BaseModel):
    story_id: str
    items: list[StoryClaim]
    total: int


# ---------------------------------------------------------------------------
# Daily Briefing (7A)
# ---------------------------------------------------------------------------

class DailyBriefing(BaseModel):
    briefing_date: Optional[str] = None       # ISO date string
    briefing_text: str
    article_count: Optional[int] = None
    top_entry_ids: Optional[str] = None       # comma-separated
    generated_at: Optional[datetime] = None
