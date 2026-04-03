import { api } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import HypeHistoryChart from "@/components/HypeHistoryChart";
import type { Metadata } from "next";
import type { TopicHistoryResponse } from "@/lib/types";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { name } = await params;
  const topic = decodeURIComponent(name);
  return { title: `${topic} Trend - SmartNews` };
}

export default async function TopicPage({ params }: Props) {
  const { name } = await params;
  const topic = decodeURIComponent(name);

  let history: TopicHistoryResponse;
  try {
    history = await api.topicHistory(topic, 30);
  } catch {
    history = {
      topic,
      days: 30,
      insufficient_data: true,
      latest_hype: null,
      latest_credibility: null,
      delta_hype_7d: null,
      delta_credibility_7d: null,
      points: [],
    };
  }

  const search = await api.search(topic, { days: 14 });

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-8">
      <section>
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold uppercase tracking-wide text-amber-700">
            Hype Decay Tracker
          </span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">{topic}</h1>
        <p className="mt-1 text-sm text-gray-500">
          Last {history.days} days trend of hype and credibility.
        </p>
      </section>

      <section>
        <HypeHistoryChart history={history} />
      </section>

      <section>
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-xl font-bold text-gray-900">Recent Coverage</h2>
          <span className="text-sm text-gray-500">{search.total} results</span>
        </div>

        {search.items.length === 0 ? (
          <p className="text-sm text-gray-500">No recent articles found for this topic.</p>
        ) : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {search.items.slice(0, 12).map((a) => (
              <ArticleCard key={a.entry_id} article={a} compact />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
