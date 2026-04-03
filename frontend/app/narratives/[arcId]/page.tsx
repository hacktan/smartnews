import { api, NotFoundError } from "@/lib/api";
import type { ArticleCard } from "@/lib/types";
import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ arcId: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { arcId } = await params;
  try {
    const arc = await api.narrative(arcId);
    return { title: `${arc.subtopic} — SmartNews` };
  } catch {
    return { title: "Narrative — SmartNews" };
  }
}

function formatDate(iso: string | null, opts?: Intl.DateTimeFormatOptions) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", opts ?? { month: "short", day: "numeric", year: "numeric" });
}

function ScoreBar({ label, value, color }: { label: string; value: number | null; color: string }) {
  if (value === null) return null;
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between text-xs text-gray-500 mb-1">
        <span>{label}</span>
        <span className={`font-semibold ${color}`}>{pct}%</span>
      </div>
      <div className="h-1.5 rounded-full bg-gray-100">
        <div className={`h-1.5 rounded-full ${color.replace("text-", "bg-")}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ArticleTimelineItem({
  article,
  index,
  isFirst,
  isLast,
}: {
  article: ArticleCard;
  index: number;
  isFirst: boolean;
  isLast: boolean;
}) {
  return (
    <div className="flex gap-4">
      {/* Timeline spine */}
      <div className="flex flex-col items-center">
        <div
          className={`flex-shrink-0 h-7 w-7 rounded-full border-2 flex items-center justify-center text-xs font-bold ${
            isFirst
              ? "border-purple-500 bg-purple-500 text-white"
              : isLast
              ? "border-blue-500 bg-blue-500 text-white"
              : "border-gray-300 bg-white text-gray-500"
          }`}
        >
          {index + 1}
        </div>
        {!isLast && <div className="w-0.5 flex-1 bg-gray-200 my-1" />}
      </div>

      {/* Card */}
      <div className={`pb-6 flex-1 ${isLast ? "" : ""}`}>
        <div className="text-xs text-gray-400 mb-1">
          {formatDate(article.published_at, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
          {article.source_name && <span className="ml-2 text-gray-500 font-medium">{article.source_name}</span>}
        </div>
        <Link href={`/article/${article.entry_id}`} className="group">
          <h3 className="text-sm font-semibold text-gray-900 group-hover:text-blue-700 transition-colors leading-snug mb-1">
            {article.title}
          </h3>
        </Link>
        {article.summary_snippet && (
          <p className="text-xs text-gray-500 line-clamp-2 mb-2">{article.summary_snippet}</p>
        )}
        <div className="flex flex-wrap gap-3 text-xs text-gray-400">
          {article.hype_score !== null && (
            <span>Hype <span className="font-semibold text-orange-500">{Math.round(article.hype_score * 100)}%</span></span>
          )}
          {article.credibility_score !== null && (
            <span>Cred <span className="font-semibold text-green-600">{Math.round(article.credibility_score * 100)}%</span></span>
          )}
          {article.importance_score !== null && (
            <span>Imp <span className="font-semibold text-blue-600">{Math.round(article.importance_score * 100)}%</span></span>
          )}
        </div>
      </div>
    </div>
  );
}

export default async function NarrativeDetailPage({ params }: Props) {
  const { arcId } = await params;
  let arc;
  try {
    arc = await api.narrative(arcId);
  } catch (err) {
    if (err instanceof NotFoundError) {
      return (
        <div className="mx-auto max-w-2xl py-24 text-center">
          <p className="text-gray-500">Narrative not found.</p>
          <Link href="/narratives" className="mt-4 inline-block text-sm text-blue-600 hover:underline">← Back to Narratives</Link>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-2xl py-24 text-center">
        <p className="text-gray-500">Could not load narrative. Please try again.</p>
        <Link href="/narratives" className="mt-4 inline-block text-sm text-blue-600 hover:underline">← Back to Narratives</Link>
      </div>
    );
  }

  const trendLabel =
    (arc.hype_trend ?? 0) > 0.05
      ? "↑ Escalating"
      : (arc.hype_trend ?? 0) < -0.05
      ? "↓ Cooling"
      : "→ Stable";
  const trendColor =
    (arc.hype_trend ?? 0) > 0.05
      ? "text-red-600 bg-red-50 border-red-200"
      : (arc.hype_trend ?? 0) < -0.05
      ? "text-green-600 bg-green-50 border-green-200"
      : "text-gray-500 bg-gray-50 border-gray-200";

  return (
    <div className="mx-auto max-w-3xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <Link href="/narratives" className="hover:text-blue-600 transition-colors">Narratives</Link>
        <span>/</span>
        <span className="text-gray-600 truncate max-w-[200px]">{arc.subtopic}</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-purple-100 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-purple-700">
            Narrative Arc
          </span>
          {arc.category && (
            <span className="rounded-full bg-gray-100 px-3 py-0.5 text-xs font-medium text-gray-600">
              {arc.category}
            </span>
          )}
          <span className={`rounded-full border px-3 py-0.5 text-xs font-semibold ${trendColor}`}>
            {trendLabel}
          </span>
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900">{arc.subtopic}</h1>
        <p className="mt-1 text-sm text-gray-400">
          {arc.article_count} articles
          {arc.first_seen && arc.last_seen && (
            <> · {formatDate(arc.first_seen)} – {formatDate(arc.last_seen)}</>
          )}
          {arc.span_days !== null && arc.span_days > 0 && (
            <> · {arc.span_days} day span</>
          )}
        </p>
      </header>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-3 mb-10">
        {/* Score summary */}
        <div className="md:col-span-1 rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400">Arc Scores</h2>
          <ScoreBar label="Importance" value={arc.avg_importance} color="text-blue-600" />
          <ScoreBar label="Credibility" value={arc.avg_credibility} color="text-green-600" />
          <ScoreBar label="Avg Hype" value={arc.avg_hype} color="text-orange-500" />

          {arc.hype_start !== null && arc.hype_end !== null && (
            <div className="pt-3 border-t border-gray-100">
              <p className="text-xs text-gray-400 mb-1">Hype evolution</p>
              <div className="flex items-center justify-between text-xs font-semibold">
                <span className="text-gray-500">Start: {Math.round(arc.hype_start * 100)}%</span>
                <span className="text-gray-400">→</span>
                <span className={arc.hype_end > arc.hype_start ? "text-red-600" : "text-green-600"}>
                  End: {Math.round(arc.hype_end * 100)}%
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Timeline */}
        <div className="md:col-span-2 rounded-xl border border-gray-200 bg-white p-5">
          <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-5">Story Timeline</h2>
          {arc.articles.length === 0 ? (
            <p className="text-sm text-gray-400">No article details available.</p>
          ) : (
            <div>
              {arc.articles.map((article, i) => (
                <ArticleTimelineItem
                  key={article.entry_id}
                  article={article}
                  index={i}
                  isFirst={i === 0}
                  isLast={i === arc.articles.length - 1}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      <p className="text-xs text-gray-400 text-center">
        Grouped by AI-extracted subtopic · Scores are signals, not verdicts
      </p>
    </div>
  );
}
