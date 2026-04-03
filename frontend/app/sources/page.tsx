import { api } from "@/lib/api";
import { ScoreBar } from "@/components/ScoreBadge";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "Source Trust Leaderboard — SmartNews",
};

export default async function SourcesLeaderboardPage() {
  const { sources } = await api.sourcesLeaderboard();

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-8">
      <div>
        <p className="text-[11px] font-semibold tracking-widest uppercase text-blue-500 mb-1.5">Rankings</p>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">Source Leaderboard</h1>
        <p className="mt-1 text-sm text-gray-400">
          Ranked by average credibility score across all analyzed articles
        </p>
      </div>

      <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
        {sources.map((source, index) => (
          <div
            key={source.source_name}
            className="flex items-center gap-4 px-5 py-4 border-b border-gray-50 last:border-0 hover:bg-gray-50/60 transition-colors"
          >
            {/* Rank */}
            <span className="w-6 shrink-0 text-sm font-bold text-gray-300 text-right">
              {index + 1}
            </span>

            {/* Source info */}
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-gray-900 truncate">{source.source_name}</p>
              <p className="text-[11px] text-gray-400 mt-0.5">{source.article_count} articles analyzed</p>
            </div>

            {/* Scores */}
            <div className="hidden sm:flex items-center gap-8 shrink-0">
              <div className="flex flex-col gap-1.5 w-28">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Credibility</span>
                  <span className="text-[11px] font-semibold text-green-600">
                    {source.avg_credibility != null ? (source.avg_credibility * 100).toFixed(0) + "%" : "—"}
                  </span>
                </div>
                <ScoreBar score={source.avg_credibility} />
              </div>
              <div className="flex flex-col gap-1.5 w-28">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Hype</span>
                  <span className="text-[11px] font-semibold text-orange-500">
                    {source.avg_hype != null ? (source.avg_hype * 100).toFixed(0) + "%" : "—"}
                  </span>
                </div>
                <ScoreBar score={source.avg_hype} type="hype" />
              </div>
            </div>

            {/* Mobile: just numbers */}
            <div className="sm:hidden flex flex-col items-end gap-1 shrink-0 text-right">
              <span className="text-[11px] text-gray-500">
                Cred <span className="font-semibold text-green-600">
                  {source.avg_credibility != null ? (source.avg_credibility * 100).toFixed(0) + "%" : "—"}
                </span>
              </span>
              <span className="text-[11px] text-gray-500">
                Hype <span className="font-semibold text-orange-500">
                  {source.avg_hype != null ? (source.avg_hype * 100).toFixed(0) + "%" : "—"}
                </span>
              </span>
            </div>
          </div>
        ))}
      </div>

      <p className="text-xs text-gray-400 text-center">
        Scores are AI-generated signals · Updated every pipeline run · Not editorial verdicts
      </p>
    </div>
  );
}
