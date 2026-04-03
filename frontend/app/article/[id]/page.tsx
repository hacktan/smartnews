import { api, NotFoundError } from "@/lib/api";
import CategoryBadge from "@/components/CategoryBadge";
import { ScorePill, ScoreBar } from "@/components/ScoreBadge";
import ArticleCard from "@/components/ArticleCard";
import { timeAgo, hypeSoftLabel, credibilitySoftLabel, importanceSoftLabel } from "@/lib/utils";
import type { Entity } from "@/lib/types";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const a = await api.article(id);
    return { title: a.title };
  } catch {
    return { title: "Article" };
  }
}

export default async function ArticlePage({ params }: Props) {
  const { id } = await params;

  let article;
  try {
    article = await api.article(id);
  } catch (err) {
    if (err instanceof NotFoundError) notFound();
    // API temporarily down (SQL warehouse idle) — show friendly message
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <h1 className="text-2xl font-bold text-gray-900">SmartNews</h1>
        <p className="text-gray-500">The news pipeline is warming up. Please check back in a moment.</p>
        <p className="text-xs text-gray-400">(The data warehouse may be resuming from idle — usually takes ~30s)</p>
        <Link href="/" className="mt-2 text-sm text-blue-600 hover:underline">← Back to Home</Link>
      </div>
    );
  }

  // Parse entities JSON
  let entities: Entity[] = [];
  if (article.entities) {
    try {
      entities = JSON.parse(article.entities);
    } catch {
      // not valid JSON — skip
    }
  }

  return (
    <article className="mx-auto max-w-3xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        {article.category && (
          <>
            <Link
              href={`/category/${article.category.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-")}`}
              className="hover:text-blue-600 transition-colors"
            >
              {article.category}
            </Link>
            <span>/</span>
          </>
        )}
        <span className="truncate text-gray-600">{article.title}</span>
      </nav>

      {/* Hero image */}
      {article.image_url && (
        <div className="mb-8 -mx-4 sm:mx-0 overflow-hidden sm:rounded-2xl bg-gray-100" style={{ maxHeight: 400 }}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={article.image_url}
            alt=""
            className="w-full object-cover"
            style={{ maxHeight: 400 }}
            onError={(e) => {
              const p = (e.target as HTMLImageElement).parentElement;
              if (p) p.style.display = "none";
            }}
          />
        </div>
      )}

      {/* Header */}
      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <CategoryBadge category={article.category} />
          {article.subtopic && (
            <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">
              {article.subtopic}
            </span>
          )}
        </div>

        <h1 className="mb-4 text-3xl font-extrabold leading-tight tracking-tight text-gray-900">
          {article.title}
        </h1>

        {/* De-Hyped headline — shown when hype_score > 0.6 and AI produced a calmer version */}
        {article.dehyped_title && article.hype_score != null && article.hype_score > 0.6 && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-green-100 bg-green-50 px-4 py-3">
            <span className="mt-0.5 shrink-0 text-xs font-semibold uppercase tracking-wide text-green-600">De-Hyped</span>
            <span className="text-sm text-gray-700 leading-relaxed">{article.dehyped_title}</span>
          </div>
        )}

        {/* Meta row */}
        <div className="flex flex-wrap items-center gap-3 text-sm text-gray-500">
          {article.source_name && (
            <span className="font-medium text-gray-700">{article.source_name}</span>
          )}
          {article.published_at && (
            <span>{timeAgo(article.published_at)}</span>
          )}
          {article.estimated_read_time_min != null && (
            <span>{article.estimated_read_time_min} min read</span>
          )}
          {article.word_count != null && (
            <span>{article.word_count.toLocaleString()} words</span>
          )}
        </div>
      </header>

      {/* Score dashboard */}
      <div className="mb-8 grid grid-cols-3 gap-2 rounded-xl border border-gray-100 bg-white p-3 shadow-sm sm:gap-4 sm:p-5">
        {[
          { label: "Credibility", score: article.credibility_score, type: "default" as const, softLabel: credibilitySoftLabel(article.credibility_score) },
          { label: "Importance", score: article.importance_score, type: "default" as const, softLabel: importanceSoftLabel(article.importance_score) },
          { label: "Hype", score: article.hype_score, type: "hype" as const, softLabel: hypeSoftLabel(article.hype_score) },
        ].map(({ label, score, type, softLabel }) => (
          <div key={label} className="flex flex-col gap-2">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              {label}
            </span>
            <ScorePill label={label} score={score} type={type} softLabel={softLabel} />
            <ScoreBar score={score} type={type} />
          </div>
        ))}
      </div>

      {/* AI Summary */}
      {article.ai_summary && (
        <section className="mb-8 rounded-xl border border-blue-100 bg-blue-50 p-5">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-blue-500">
            AI Summary
          </h2>
          <p className="text-gray-800 leading-relaxed">{article.ai_summary}</p>
        </section>
      )}

      {/* Why It Matters */}
      {article.why_it_matters && (
        <section className="mb-8 rounded-xl border border-amber-100 bg-amber-50 p-5">
          <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-amber-600">
            Why It Matters
          </h2>
          <p className="text-gray-800 leading-relaxed">{article.why_it_matters}</p>
        </section>
      )}

      {/* Clean summary */}
      {article.clean_summary && (
        <section className="mb-8">
          <h2 className="mb-3 text-lg font-bold text-gray-900">Summary</h2>
          <p className="leading-relaxed text-gray-700 whitespace-pre-line">{article.clean_summary}</p>
        </section>
      )}

      {/* Entities */}
      {entities.length > 0 && (
        <section className="mb-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-400">
            Key Entities
          </h2>
          <div className="flex flex-wrap gap-2">
            {entities.map((e, i) => (
              <Link
                key={i}
                href={`/entity/${encodeURIComponent(e.name)}`}
                className="rounded-full border border-gray-200 bg-white px-3 py-1 text-sm text-gray-700 hover:border-blue-300 hover:text-blue-700 transition-colors"
              >
                <span className="mr-1 text-xs text-gray-400">{e.type}</span>
                {e.name}
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Read full article */}
      {article.link && (
        <div className="flex justify-center">
          <a
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-xl bg-blue-600 px-8 py-3 text-sm font-semibold text-white transition hover:bg-blue-700"
          >
            Read Full Article →
          </a>
        </div>
      )}

      {/* Related Articles */}
      {article.related_articles && article.related_articles.length > 0 && (
        <section className="mt-12 border-t border-gray-100 pt-8">
          <h2 className="mb-4 text-lg font-bold text-gray-900">Related Stories</h2>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            {article.related_articles.map((a) => (
              <ArticleCard key={a.entry_id} article={a} compact />
            ))}
          </div>
        </section>
      )}
    </article>
  );
}
