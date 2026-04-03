import { api, NotFoundError } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Daily Briefing — SmartNews" };

function formatDate(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  return d.toLocaleDateString("en-US", { weekday: "long", year: "numeric", month: "long", day: "numeric" });
}

function renderBullets(text: string) {
  // Split on lines starting with "- " or "• " and render each as a block
  const lines = text.split("\n").filter((l) => l.trim().length > 0);
  return lines.map((line, i) => {
    // Strip leading dash/bullet
    const clean = line.replace(/^[-•]\s*/, "");
    // Bold markdown: **text:** → <strong>text:</strong>
    const parts = clean.split(/(\*\*[^*]+\*\*)/g);
    return (
      <li key={i} className="flex gap-3 py-4 border-b border-gray-100 last:border-0">
        <span className="mt-2 flex-shrink-0 h-2 w-2 rounded-full bg-blue-500" />
        <p className="text-gray-800 leading-relaxed">
          {parts.map((part, j) =>
            part.startsWith("**") && part.endsWith("**") ? (
              <strong key={j} className="text-gray-900">
                {part.slice(2, -2)}
              </strong>
            ) : (
              part
            )
          )}
        </p>
      </li>
    );
  });
}

export default async function BriefingPage() {
  let briefing;
  try {
    briefing = await api.dailyBriefing();
  } catch (err) {
    if (err instanceof NotFoundError) {
      return (
        <div className="mx-auto max-w-2xl py-24 text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Daily Briefing</h1>
          <p className="text-gray-500 mb-2">No briefing available yet.</p>
          <p className="text-xs text-gray-400">The pipeline will generate one on its next run.</p>
          <Link href="/" className="mt-6 inline-block text-sm text-blue-600 hover:underline">← Back to Home</Link>
        </div>
      );
    }
    return (
      <div className="mx-auto max-w-2xl py-24 text-center">
        <p className="text-gray-500">The news pipeline is warming up. Please check back in a moment.</p>
        <Link href="/" className="mt-4 inline-block text-sm text-blue-600 hover:underline">← Back to Home</Link>
      </div>
    );
  }

  const articleIds = briefing.top_entry_ids
    ? briefing.top_entry_ids.split(",").filter(Boolean)
    : [];

  // Fetch source articles in parallel for rich display
  const sourceArticles = await Promise.all(
    articleIds.map((id) => api.article(id).catch(() => null))
  ).then((results) => results.filter(Boolean));

  return (
    <div className="mx-auto max-w-2xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <span className="text-gray-600">Daily Briefing</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-blue-100 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-blue-700">
            AI Briefing
          </span>
          {briefing.article_count != null && (
            <span className="text-xs text-gray-400">
              synthesized from {briefing.article_count} stories
            </span>
          )}
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          Today&apos;s Signal
        </h1>
        {briefing.briefing_date && (
          <p className="mt-1 text-sm text-gray-400">{formatDate(briefing.briefing_date)}</p>
        )}
      </header>

      {/* Briefing bullets */}
      <section className="mb-8 rounded-xl border border-blue-100 bg-blue-50 px-6 py-2">
        <ul className="divide-y divide-blue-100">
          {renderBullets(briefing.briefing_text)}
        </ul>
      </section>

      {/* Source articles */}
      {sourceArticles.length > 0 && (
        <section>
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-gray-400">
            Source Articles ({sourceArticles.length})
          </h2>
          <div className="rounded-2xl bg-white border border-gray-100 shadow-sm px-5">
            {sourceArticles.map((article) => article && (
              <ArticleCard
                key={article.entry_id}
                article={{
                  entry_id: article.entry_id,
                  title: article.title,
                  source_name: article.source_name ?? "",
                  published_at: article.published_at,
                  category: article.category,
                  summary_snippet: article.ai_summary || article.clean_summary,
                  hype_score: article.hype_score,
                  credibility_score: article.credibility_score,
                  importance_score: article.importance_score,
                  link: article.link,
                  publish_date: null,
                  image_url: article.image_url ?? null,
                }}
                compact
              />
            ))}
          </div>
        </section>
      )}

      {/* Disclaimer */}
      <p className="mt-10 text-xs text-gray-400 text-center">
        Generated by AI · Updated every pipeline run · Scores are signals, not verdicts
      </p>
    </div>
  );
}
