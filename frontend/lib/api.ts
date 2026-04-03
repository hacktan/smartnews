import type {
  HomeResponse,
  CategoriesResponse,
  CategoryFeedResponse,
  ArticleDetail,
  SearchResponse,
  SourceLeaderboardResponse,
  StoryCluster,
  StoryClusterDetail,
  EntityResponse,
  TopEntitiesResponse,
  BlindSpotsResponse,
  DailyBriefing,
  TopicHistoryResponse,
  NarrativesResponse,
  NarrativeDetail,
  CompiledStoriesResponse,
  CompiledStoryDetail,
} from "./types";

const BASE = (
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).replace(/\/$/, "");

export class NotFoundError extends Error {
  constructor(path: string) {
    super(`API ${path} → 404`);
    this.name = "NotFoundError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    next: { revalidate: 180 }, // 3-min ISR — matches API cache TTL
    ...init,
  });
  if (!res.ok) {
    if (res.status === 404) throw new NotFoundError(path);
    throw new Error(`API ${path} → ${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  home: () => apiFetch<HomeResponse>("/api/home"),

  categories: () => apiFetch<CategoriesResponse>("/api/categories"),

  categoryFeed: (slug: string, page = 1, pageSize = 20) =>
    apiFetch<CategoryFeedResponse>(
      `/api/category/${slug}?page=${page}&page_size=${pageSize}`
    ),

  article: (id: string) =>
    apiFetch<ArticleDetail>(`/api/article/${id}`, { next: { revalidate: 600 } }),

  search: (
    q: string,
    opts?: {
      category?: string;
      source?: string;
      days?: number;
      min_credibility?: number;
      max_hype?: number;
      min_importance?: number;
    }
  ) => {
    const params = new URLSearchParams({ q });
    if (opts?.category) params.set("category", opts.category);
    if (opts?.source) params.set("source", opts.source);
    if (opts?.days) params.set("days", String(opts.days));
    if (opts?.min_credibility)
      params.set("min_credibility", String(opts.min_credibility));
    if (opts?.max_hype) params.set("max_hype", String(opts.max_hype));
    if (opts?.min_importance)
      params.set("min_importance", String(opts.min_importance));
    return apiFetch<SearchResponse>(`/api/search?${params}`, {
      cache: "no-store",
    });
  },

  sourcesLeaderboard: () =>
    apiFetch<SourceLeaderboardResponse>("/api/sources/leaderboard"),

  clusters: () =>
    apiFetch<StoryCluster[]>("/api/clusters"),

  cluster: (id: number) =>
    apiFetch<StoryClusterDetail>(`/api/clusters/${id}`),

  topEntities: (limit = 30) =>
    apiFetch<TopEntitiesResponse>(`/api/entities?limit=${limit}`),

  entity: (name: string) =>
    apiFetch<EntityResponse>(`/api/entity/${encodeURIComponent(name)}`, {
      next: { revalidate: 120 },
    }),

  blindSpots: (limit = 12) =>
    apiFetch<BlindSpotsResponse>(`/api/insights/blind-spots?limit=${limit}`),

  dailyBriefing: () =>
    apiFetch<DailyBriefing>("/api/briefing/daily"),

  topicHistory: (topic: string, days = 30) =>
    apiFetch<TopicHistoryResponse>(
      `/api/topics/${encodeURIComponent(topic)}/history?days=${days}`
    ),

  narratives: (limit = 20) =>
    apiFetch<NarrativesResponse>(`/api/narratives?limit=${limit}`),

  narrative: (arcId: string) =>
    apiFetch<NarrativeDetail>(`/api/narratives/${arcId}`),

  compiledStories: (limit = 20) =>
    apiFetch<CompiledStoriesResponse>(`/api/stories?limit=${limit}`),

  compiledStory: (storyId: string) =>
    apiFetch<CompiledStoryDetail>(`/api/story/${storyId}`),
};
