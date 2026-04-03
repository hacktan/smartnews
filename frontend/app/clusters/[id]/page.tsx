import { api } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import HypeHistoryChart from "@/components/HypeHistoryChart";
import { notFound } from "next/navigation";
import type { Metadata } from "next";
import Link from "next/link";
import type { TopicHistoryResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  return { title: `Story Cluster #${id} — SmartNews` };
}

export default async function ClusterPage({ params }: Props) {
  const { id } = await params;
  const clusterId = parseInt(id, 10);
  if (isNaN(clusterId)) notFound();

  let cluster;
  try {
    cluster = await api.cluster(clusterId);
  } catch {
    notFound();
  }

  const topic = cluster.primary_topic || cluster.top_categories || "";
  let history: TopicHistoryResponse = {
    topic,
    days: 30,
    insufficient_data: true,
    latest_hype: null,
    latest_credibility: null,
    delta_hype_7d: null,
    delta_credibility_7d: null,
    points: [],
  };
  if (topic) {
    try {
      history = await api.topicHistory(topic, 30);
    } catch {
      // keep fallback; cluster page should never fail because history is unavailable
    }
  }

  return (
    <div className="mx-auto max-w-4xl flex flex-col gap-8">
      {/* Header */}
      <div>
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700 uppercase tracking-wide">
            Story Cluster
          </span>
          <span className="text-sm text-gray-400">#{cluster.cluster_id + 1}</span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">
          {cluster.label ?? `Cluster ${cluster.cluster_id + 1}`}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {cluster.article_count} articles grouped by topic similarity
        </p>

        {/* Score pills */}
        <div className="mt-4 flex flex-wrap gap-3">
          {cluster.avg_importance != null && (
            <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-medium text-blue-700">
              Importance {(cluster.avg_importance * 100).toFixed(0)}%
            </span>
          )}
          {cluster.avg_credibility != null && (
            <span className="rounded-full bg-green-50 px-3 py-1 text-xs font-medium text-green-700">
              Credibility {(cluster.avg_credibility * 100).toFixed(0)}%
            </span>
          )}
          {cluster.avg_hype != null && (
            <span className="rounded-full bg-orange-50 px-3 py-1 text-xs font-medium text-orange-700">
              Hype {(cluster.avg_hype * 100).toFixed(0)}%
            </span>
          )}
        </div>
      </div>

      {/* Topic Trend */}
      {topic && (
        <section className="rounded-xl border border-gray-100 bg-gray-50 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-lg font-bold text-gray-900">Topic Trend</h2>
              <p className="text-sm text-gray-500">
                Primary topic: <span className="font-medium text-gray-700">{topic}</span>
              </p>
            </div>
            <Link
              href={`/topic/${encodeURIComponent(topic)}`}
              className="text-sm font-medium text-blue-600 hover:underline"
            >
              View trend →
            </Link>
          </div>
          <HypeHistoryChart history={history} />
        </section>
      )}

      {/* Articles */}
      {cluster.articles.length === 0 ? (
        <p className="text-gray-400">No articles found in this cluster.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {cluster.articles.map((a) => (
            <ArticleCard key={a.entry_id} article={a} />
          ))}
        </div>
      )}
    </div>
  );
}
