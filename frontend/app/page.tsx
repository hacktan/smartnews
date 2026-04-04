import { api } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import TrendingTopics from "@/components/TrendingTopics";
import { categorySlug, timeAgo } from "@/lib/utils";
import Link from "next/link";
import type { Metadata } from "next";
import type { StoryCluster, BlindSpotItem, NarrativeArc } from "@/lib/types";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "SmartNews — AI-curated Tech News" };

function SectionHeader({
  title,
  subtitle,
  href,
  hrefLabel = "See all",
  eyebrow,
}: {
  title: string;
  subtitle?: string;
  href?: string;
  hrefLabel?: string;
  eyebrow?: string;
}) {
  return (
    <div className="flex items-end justify-between mb-5">
      <div className="flex flex-col gap-0.5">
        {eyebrow && (
          <p className="text-[11px] font-semibold tracking-widest uppercase text-blue-500 mb-0.5">{eyebrow}</p>
        )}
        <h2 className="text-xl font-bold tracking-tight text-gray-900">{title}</h2>
        {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
      </div>
      {href && (
        <Link href={href} className="text-xs font-medium text-blue-600 hover:text-blue-800 transition-colors pb-0.5 shrink-0 ml-4">
          {hrefLabel} →
        </Link>
      )}
    </div>
  );
}

export default async function HomePage() {
  let home;
  let clusters: StoryCluster[] = [];
  let blindSpots: BlindSpotItem[] = [];
  let narratives: NarrativeArc[] = [];

  try {
    home = await api.home();
  } catch {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-32 text-center">
        <div className="w-12 h-12 rounded-2xl bg-blue-50 flex items-center justify-center mb-1">
          <svg className="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
              d="M19.5 12c0-3.866-3.134-7-7-7S5.5 8.134 5.5 12s3.134 7 7 7" />
          </svg>
        </div>
        <h1 className="text-xl font-semibold text-gray-900">Pipeline warming up</h1>
        <p className="text-sm text-gray-400 max-w-xs">
          The data warehouse is resuming from idle — usually takes about 30 seconds.
        </p>
      </div>
    );
  }

  try { clusters = await api.clusters(); } catch { clusters = []; }
  try { const bs = await api.blindSpots(8); blindSpots = bs.items; } catch { blindSpots = []; }
  try {
    const nr = await api.narratives(6);
    const items = Array.isArray(nr.items) ? nr.items : [];
    narratives = items.filter((a) => (a.hype_trend ?? 0) > 0.05).slice(0, 4);
  } catch {
    narratives = [];
  }

  return (
    <div className="flex flex-col gap-14">

      {/* ── Top Stories ─────────────────────────────────────── */}
      <section>
        <div className="mb-6">
          <p className="text-[11px] font-semibold tracking-widest uppercase text-blue-500 mb-1.5">AI Enriched</p>
          <h1 className="text-3xl font-extrabold tracking-tight text-gray-900 leading-tight">Top Stories</h1>
          <p className="text-sm text-gray-400 mt-1">Ranked by importance score</p>
        </div>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {home.top_stories.map((a) => (
            <ArticleCard key={a.entry_id} article={a} />
          ))}
        </div>
      </section>

      {/* ── Low Hype + Trending ─────────────────────────────── */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <section className="lg:col-span-2">
          <SectionHeader
            title="Low Hype Picks"
            subtitle="Important stories flying under the radar"
          />
          <div className="rounded-2xl bg-white border border-gray-100 shadow-sm px-5">
            {home.low_hype_picks.map((a) => (
              <ArticleCard key={a.entry_id} article={a} compact />
            ))}
          </div>
        </section>
        <aside>
          <TrendingTopics topics={home.trending_topics} />
        </aside>
      </div>

      {/* ── Latest Briefs ────────────────────────────────────── */}
      <section>
        <SectionHeader title="Latest Briefs" subtitle="Most recently published" />
        <div className="rounded-2xl bg-white border border-gray-100 shadow-sm px-5">
          {home.latest_briefs.map((a) => (
            <ArticleCard key={a.entry_id} article={a} compact />
          ))}
        </div>
      </section>

      {/* ── Story Clusters ───────────────────────────────────── */}
      {clusters.length > 0 && (
        <section>
          <SectionHeader
            title="Story Clusters"
            subtitle="Articles grouped by topic similarity"
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {clusters.slice(0, 6).map((cluster) => (
              <Link
                key={cluster.cluster_id}
                href={`/clusters/${cluster.cluster_id}`}
                className="group flex flex-col gap-3 rounded-2xl border border-gray-100 bg-white p-5 shadow-sm hover:shadow-[0_4px_20px_rgba(0,0,0,0.07)] hover:border-indigo-100 transition-all duration-200"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-600 tracking-wide">
                    {cluster.top_categories ?? "General"}
                  </span>
                  <span className="text-[11px] text-gray-400 shrink-0 mt-1">{cluster.article_count} articles</span>
                </div>
                <p className="text-sm font-semibold text-gray-800 group-hover:text-indigo-700 leading-snug line-clamp-2 transition-colors">
                  {cluster.label ?? `Cluster ${cluster.cluster_id + 1}`}
                </p>
                <div className="flex items-center gap-3 mt-auto">
                  {cluster.avg_importance != null && (
                    <span className="text-[11px] text-gray-400">
                      Impact <span className="font-semibold text-gray-600">{(cluster.avg_importance * 100).toFixed(0)}%</span>
                    </span>
                  )}
                  {cluster.avg_hype != null && (
                    <span className="text-[11px] text-gray-400">
                      Hype <span className="font-semibold text-gray-600">{(cluster.avg_hype * 100).toFixed(0)}%</span>
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ── Blind Spots ─────────────────────────────────────── */}
      {blindSpots.length > 0 && (
        <section>
          <SectionHeader
            title="Blind Spots"
            subtitle="Important stories covered by only one source"
          />
          <div className="rounded-2xl border border-amber-100 bg-amber-50/70 overflow-hidden">
            {blindSpots.map((item) => (
              <Link
                key={item.entry_id}
                href={`/article/${item.entry_id}`}
                className="flex items-start justify-between gap-4 px-5 py-4 border-b border-amber-100 last:border-0 hover:bg-amber-100/60 transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-semibold text-gray-900 leading-snug line-clamp-2">
                    {item.title}
                  </p>
                  <div className="mt-1.5 flex flex-wrap items-center gap-x-2 gap-y-1">
                    {item.source_name && (
                      <span className="text-[11px] font-medium text-gray-600">{item.source_name}</span>
                    )}
                    {item.category && (
                      <span className="text-[11px] text-gray-400">{item.category}</span>
                    )}
                    {item.published_at && (
                      <span className="text-[11px] text-gray-400">{timeAgo(item.published_at)}</span>
                    )}
                  </div>
                </div>
                <div className="shrink-0 flex flex-col items-end gap-1.5 pt-0.5">
                  <span className="rounded-full bg-amber-200 px-2.5 py-0.5 text-[11px] font-semibold text-amber-800">
                    1 source
                  </span>
                  {item.importance_score != null && (
                    <span className="text-[11px] text-gray-400">
                      {(item.importance_score * 100).toFixed(0)}% impact
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        </section>
      )}


      {/* ── Escalating Narratives ────────────────────────────── */}
      {narratives.length > 0 && (
        <section>
          <SectionHeader
            title="Escalating Stories"
            subtitle="Hype is rising on these narratives"
            href="/narratives"
            hrefLabel="All narratives"
            eyebrow="Hype Tracker"
          />
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {narratives.map((arc) => (
              <Link
                key={arc.arc_id}
                href={`/narratives/${arc.arc_id}`}
                className="group flex flex-col gap-2 rounded-2xl border border-red-100 bg-red-50/50 p-5 hover:border-red-200 hover:bg-red-50 transition-all"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="rounded-full bg-red-100 px-2.5 py-0.5 text-[11px] font-semibold text-red-700">
                    ↑ Escalating
                  </span>
                  <span className="text-[11px] text-gray-400 shrink-0">{arc.article_count} articles</span>
                </div>
                <p className="text-sm font-semibold text-gray-800 group-hover:text-red-700 leading-snug line-clamp-2 transition-colors">
                  {arc.subtopic}
                </p>
                {arc.latest_title && (
                  <p className="text-[12px] text-gray-500 line-clamp-1">{arc.latest_title}</p>
                )}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* ── Category Rows ────────────────────────────────────── */}
      {Object.entries(home.category_rows ?? {}).map(([category, articles]) => (
        <section key={category}>
          <SectionHeader
            title={category}
            subtitle="Top stories by importance"
            href={`/category/${categorySlug(category)}`}
          />
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {articles.slice(0, 3).map((a) => (
              <ArticleCard key={a.entry_id} article={a} />
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
