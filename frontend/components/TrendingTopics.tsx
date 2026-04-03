import Link from "next/link";
import { timeAgo } from "@/lib/utils";
import type { TrendingTopic } from "@/lib/types";

interface Props {
  topics: TrendingTopic[];
}

export default function TrendingTopics({ topics }: Props) {
  if (!topics.length) return null;
  return (
    <div className="rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
      <div className="px-5 pt-5 pb-3">
        <p className="text-[11px] font-semibold tracking-widest uppercase text-gray-400 mb-0.5">
          Trending
        </p>
        <h2 className="text-base font-bold text-gray-900">Hot Topics</h2>
      </div>
      <ol className="divide-y divide-gray-50">
        {topics.map((t, i) => (
          <li key={t.topic} className="flex items-start gap-3 px-5 py-3.5 hover:bg-gray-50/60 transition-colors">
            <span className="mt-0.5 w-5 shrink-0 text-right text-sm font-bold text-gray-200">
              {i + 1}
            </span>
            <div className="flex-1 min-w-0">
              <Link
                href={`/search?q=${encodeURIComponent(t.topic)}`}
                className="text-sm font-semibold text-gray-900 hover:text-blue-600 transition-colors leading-snug line-clamp-2 block"
              >
                {t.topic}
              </Link>
              <div className="flex items-center gap-2 mt-1 flex-wrap">
                <span className="text-[11px] text-gray-400">{t.article_count} articles</span>
                {t.latest_at && (
                  <span className="text-[11px] text-gray-400">· {timeAgo(t.latest_at)}</span>
                )}
                {t.category && (
                  <span className="text-[11px] text-gray-400">· {t.category}</span>
                )}
              </div>
            </div>
          </li>
        ))}
      </ol>
    </div>
  );
}
