// TypeScript types mirroring the FastAPI Pydantic models

export interface ArticleCard {
  entry_id: string;
  title: string;
  source_name: string;
  published_at: string | null;
  category: string | null;
  summary_snippet: string | null;
  hype_score: number | null;
  credibility_score: number | null;
  importance_score: number | null;
  link: string | null;
  publish_date: string | null;
  image_url: string | null;
}

export interface ArticleDetail {
  entry_id: string;
  title: string;
  dehyped_title: string | null;
  source_name: string | null;
  published_at: string | null;
  category: string | null;
  link: string | null;
  clean_summary: string | null;
  full_text: string | null;
  has_full_text: boolean | null;
  ai_summary: string | null;
  why_it_matters: string | null;
  hype_score: number | null;
  credibility_score: number | null;
  importance_score: number | null;
  freshness_score: number | null;
  entities: string | null; // JSON string: [{name, type}]
  subtopic: string | null;
  language: string | null;
  word_count: number | null;
  estimated_read_time_min: number | null;
  image_url: string | null;
  related_articles: ArticleCard[];
}

export interface TrendingTopic {
  topic: string;
  article_count: number;
  top_source: string | null;
  latest_at: string | null;
  category: string | null;
}

export interface HomeResponse {
  top_stories: ArticleCard[];
  low_hype_picks: ArticleCard[];
  trending_topics: TrendingTopic[];
  latest_briefs: ArticleCard[];
  category_rows: Record<string, ArticleCard[]>;
}

export interface CategoryMeta {
  slug: string;
  label: string;
  article_count: number;
}

export interface CategoriesResponse {
  categories: CategoryMeta[];
}

export interface CategoryFeedItem {
  entry_id: string;
  category: string;
  published_at: string | null;
  importance_score: number | null;
  hype_score: number | null;
  credibility_score: number | null;
  title: string;
  summary_snippet: string | null;
  source_name: string | null;
  image_url: string | null;
}

export interface CategoryFeedResponse {
  category: string;
  slug: string;
  page: number;
  page_size: number;
  total: number;
  items: CategoryFeedItem[];
}

export interface SearchResponse {
  query: string;
  total: number;
  items: ArticleCard[];
}

export interface Entity {
  name: string;
  type: string;
}

export interface SourceLeaderboardItem {
  source_name: string;
  article_count: number;
  avg_credibility: number | null;
  avg_hype: number | null;
  avg_importance: number | null;
}

export interface SourceLeaderboardResponse {
  sources: SourceLeaderboardItem[];
}

export interface StoryCluster {
  cluster_id: number;
  label: string | null;
  article_count: number;
  top_entry_ids: string | null;  // comma-separated
  top_categories: string | null;
  avg_importance: number | null;
  avg_credibility: number | null;
  avg_hype: number | null;
}

export interface StoryClusterDetail extends StoryCluster {
  primary_topic?: string | null;
  articles: ArticleCard[];
}

export interface EntityArticle {
  entry_id: string;
  title: string;
  source_name: string | null;
  category: string | null;
  published_at: string | null;
  hype_score: number | null;
  credibility_score: number | null;
  importance_score: number | null;
}

export interface EntityResponse {
  entity_name: string;
  entity_type: string | null;
  article_count: number;
  avg_hype: number | null;
  avg_credibility: number | null;
  avg_importance: number | null;
  articles: EntityArticle[];
}

export interface EntitySummary {
  entity_name: string;
  entity_type: string | null;
  article_count: number;
  avg_credibility: number | null;
  avg_hype: number | null;
}

export interface TopEntitiesResponse {
  entities: EntitySummary[];
}

export interface BlindSpotItem {
  entity_name: string;
  entity_type: string | null;
  entry_id: string;
  title: string;
  source_name: string | null;
  category: string | null;
  published_at: string | null;
  importance_score: number | null;
  hype_score: number | null;
  credibility_score: number | null;
}

export interface BlindSpotsResponse {
  items: BlindSpotItem[];
}

export interface DailyBriefing {
  briefing_date: string | null;
  briefing_text: string;
  article_count: number | null;
  top_entry_ids: string | null;
  generated_at: string | null;
}

export interface TopicHistoryPoint {
  snapshot_date: string;
  article_count: number;
  avg_hype: number | null;
  avg_credibility: number | null;
  avg_importance: number | null;
}

export interface TopicHistoryResponse {
  topic: string;
  days: number;
  insufficient_data: boolean;
  latest_hype: number | null;
  latest_credibility: number | null;
  delta_hype_7d: number | null;
  delta_credibility_7d: number | null;
  points: TopicHistoryPoint[];
}

export interface NarrativeArc {
  arc_id: string;
  subtopic: string;
  category: string | null;
  article_count: number;
  first_seen: string | null;
  last_seen: string | null;
  span_days: number | null;
  hype_start: number | null;
  hype_end: number | null;
  hype_trend: number | null;
  avg_importance: number | null;
  avg_hype: number | null;
  avg_credibility: number | null;
  latest_title: string | null;
}

export interface NarrativeDetail extends NarrativeArc {
  entry_ids: string[];
  titles: string[];
  articles: ArticleCard[];
}

export interface NarrativesResponse {
  items: NarrativeArc[];
  total: number;
}

// ---------------------------------------------------------------------------
// Compiled Stories (Layer 8 — AI multi-source synthesis)
// ---------------------------------------------------------------------------

export interface CompiledStory {
  story_id: string;
  compiled_title: string | null;
  compiled_summary: string | null;
  source_count: number | null;
  sources_used: string | null;   // JSON list of source names
  category: string | null;
  first_published: string | null;
  last_published: string | null;
  compiled_at: string | null;
  entry_ids: string | null;      // JSON list of entry_ids
}

export interface CompiledStoryDetail extends CompiledStory {
  compiled_body: string | null;
  key_claims: string | null;         // JSON
  consensus_points: string | null;   // JSON
  divergence_points: string | null;  // JSON
  source_articles: ArticleCard[];
}

export interface CompiledStoriesResponse {
  items: CompiledStory[];
  total: number;
}

export interface StoryClaim {
  story_id: string;
  claim_group_id: string;
  claim_text: string;
  claim_normalized: string | null;
  verdict: "CONSENSUS" | "DISPUTED" | "SINGLE_SOURCE";
  confidence: number | null;
  confirm_count: number | null;
  dispute_count: number | null;
  sources_confirming: string | null; // JSON list
  sources_disputing: string | null;  // JSON list
  entry_ids: string | null;          // JSON list
}

export interface StoryClaimsResponse {
  story_id: string;
  items: StoryClaim[];
  total: number;
}
