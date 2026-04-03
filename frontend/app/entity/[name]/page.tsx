import { api, NotFoundError } from "@/lib/api";
import { ScorePill } from "@/components/ScoreBadge";
import {
  timeAgo,
  credibilitySoftLabel,
  hypeSoftLabel,
  importanceSoftLabel,
} from "@/lib/utils";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ name: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { name } = await params;
  const decoded = decodeURIComponent(name);
  return { title: `${decoded} — Entity · SmartNews` };
}

const TYPE_COLORS: Record<string, string> = {
  PERSON: "bg-blue-100 text-blue-700",
  ORG: "bg-purple-100 text-purple-700",
  PLACE: "bg-green-100 text-green-700",
  PRODUCT: "bg-orange-100 text-orange-700",
  EVENT: "bg-red-100 text-red-700",
};

export default async function EntityPage({ params }: Props) {
  const { name } = await params;
  const decoded = decodeURIComponent(name);

  let entity;
  try {
    entity = await api.entity(decoded);
  } catch (err) {
    if (err instanceof NotFoundError) notFound();
    return (
      <div className="flex flex-col items-center justify-center gap-4 py-24 text-center">
        <p className="text-gray-500">The news pipeline is warming up. Please check back in a moment.</p>
        <Link href="/" className="text-sm text-blue-600 hover:underline">← Back to Home</Link>
      </div>
    );
  }

  const typeColor =
    TYPE_COLORS[entity.entity_type ?? ""] ?? "bg-gray-100 text-gray-600";

  return (
    <div className="mx-auto max-w-3xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <span className="text-gray-600">Entities</span>
        <span>/</span>
        <span className="text-gray-800 font-medium">{entity.entity_name}</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-3 flex items-center gap-3">
          {entity.entity_type && (
            <span className={`rounded-full px-3 py-0.5 text-xs font-semibold uppercase tracking-wide ${typeColor}`}>
              {entity.entity_type}
            </span>
          )}
          <span className="text-sm text-gray-400">
            {entity.article_count} article{entity.article_count !== 1 ? "s" : ""}
          </span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          {entity.entity_name}
        </h1>
      </header>

      {/* Aggregate score dashboard */}
      <div className="mb-8 grid grid-cols-3 gap-4 rounded-xl border border-gray-100 bg-white p-5 shadow-sm">
        {[
          {
            label: "Avg Credibility",
            score: entity.avg_credibility,
            type: "default" as const,
            softLabel: credibilitySoftLabel(entity.avg_credibility),
          },
          {
            label: "Avg Importance",
            score: entity.avg_importance,
            type: "default" as const,
            softLabel: importanceSoftLabel(entity.avg_importance),
          },
          {
            label: "Avg Hype",
            score: entity.avg_hype,
            type: "hype" as const,
            softLabel: hypeSoftLabel(entity.avg_hype),
          },
        ].map(({ label, score, type, softLabel }) => (
          <div key={label} className="flex flex-col gap-1">
            <span className="text-xs font-semibold uppercase tracking-wide text-gray-400">
              {label}
            </span>
            <ScorePill label="" score={score} type={type} softLabel={softLabel} className="text-sm font-bold" />
          </div>
        ))}
      </div>

      {/* Article list */}
      <section>
        <h2 className="mb-4 text-lg font-bold text-gray-900">
          Articles mentioning {entity.entity_name}
        </h2>
        <div className="flex flex-col divide-y divide-gray-100">
          {entity.articles.map((a) => (
            <article key={a.entry_id} className="py-4">
              <div className="flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/article/${a.entry_id}`}
                    className="block font-semibold text-gray-900 hover:text-blue-600 transition-colors leading-snug mb-1"
                  >
                    {a.title}
                  </Link>
                  <div className="flex flex-wrap items-center gap-2 text-xs text-gray-400">
                    {a.source_name && (
                      <span className="font-medium text-gray-600">{a.source_name}</span>
                    )}
                    {a.category && (
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-500">
                        {a.category}
                      </span>
                    )}
                    {a.published_at && <span>{timeAgo(a.published_at)}</span>}
                  </div>
                </div>
                {/* Mini score pills */}
                <div className="flex shrink-0 flex-col gap-1 text-right">
                  {a.credibility_score != null && (
                    <ScorePill
                      label="Cred"
                      score={a.credibility_score}
                      type="default"
                      softLabel={credibilitySoftLabel(a.credibility_score)}
                      className="text-xs"
                    />
                  )}
                  {a.hype_score != null && (
                    <ScorePill
                      label="Hype"
                      score={a.hype_score}
                      type="hype"
                      softLabel={hypeSoftLabel(a.hype_score)}
                      className="text-xs"
                    />
                  )}
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
