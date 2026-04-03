import Link from "next/link";
import { timeAgo, categorySlug, hypeSoftLabel, credibilitySoftLabel, importanceSoftLabel } from "@/lib/utils";
import { ScorePill } from "./ScoreBadge";
import CategoryBadge from "./CategoryBadge";
import ClickTracker from "./ClickTracker";
import type { ArticleCard as ArticleCardType } from "@/lib/types";

interface Props {
  article: ArticleCardType;
  compact?: boolean;
}

export default function ArticleCard({ article, compact = false }: Props) {
  /* ── Compact — horizontal list item ─────────────────────────────────── */
  if (compact) {
    return (
      <article className="group flex items-start gap-3 py-4 border-b border-gray-100 last:border-0">
        {/* Text */}
        <div className="flex-1 min-w-0 flex flex-col gap-1.5">
          <div className="flex items-center gap-2 min-w-0">
            {article.category && (
              <Link href={`/category/${categorySlug(article.category)}`} className="shrink-0">
                <CategoryBadge category={article.category} />
              </Link>
            )}
            <span className="text-[11px] text-gray-400 truncate">
              {article.source_name}&nbsp;·&nbsp;{timeAgo(article.published_at)}
            </span>
          </div>

          <ClickTracker entryId={article.entry_id} source="card">
            <Link href={`/article/${article.entry_id}`}>
              <h3 className="text-sm font-semibold leading-snug text-gray-900 line-clamp-2 group-hover:text-blue-600 transition-colors duration-150">
                {article.title}
              </h3>
            </Link>
          </ClickTracker>

          <div className="flex items-center gap-3 mt-0.5">
            <ScorePill label="Cred"   score={article.credibility_score} softLabel={credibilitySoftLabel(article.credibility_score)} />
            <ScorePill label="Hype"   score={article.hype_score}        softLabel={hypeSoftLabel(article.hype_score)}        type="hype" />
            <ScorePill label="Impact" score={article.importance_score}  softLabel={importanceSoftLabel(article.importance_score)} />
          </div>
        </div>

        {/* Thumbnail */}
        {article.image_url && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={article.image_url}
            alt=""
            className="shrink-0 w-[72px] h-[72px] rounded-xl object-cover bg-gray-100"
            loading="lazy"
            onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }}
          />
        )}
      </article>
    );
  }

  /* ── Full — vertical card ────────────────────────────────────────────── */
  return (
    <article className="group flex flex-col rounded-2xl bg-white border border-gray-100 shadow-sm hover:shadow-[0_8px_30px_rgba(0,0,0,0.08)] hover:border-gray-200 transition-all duration-200 overflow-hidden">
      {/* Cover image */}
      {article.image_url && (
        <div className="relative h-44 shrink-0 overflow-hidden bg-gray-100">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={article.image_url}
            alt=""
            className="absolute inset-0 w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.04]"
            loading="lazy"
            onError={(e) => {
              const p = (e.target as HTMLImageElement).parentElement;
              if (p) p.style.display = "none";
            }}
          />
        </div>
      )}

      {/* Body */}
      <div className="flex flex-col flex-1 p-5 gap-0">
        {/* Meta */}
        <div className="flex items-center gap-2 mb-3 min-w-0">
          {article.category && (
            <Link href={`/category/${categorySlug(article.category)}`} className="shrink-0">
              <CategoryBadge category={article.category} />
            </Link>
          )}
          <span className="text-[11px] text-gray-400 truncate">
            {article.source_name}&nbsp;·&nbsp;{timeAgo(article.published_at)}
          </span>
        </div>

        {/* Title */}
        <ClickTracker entryId={article.entry_id} source="card">
          <Link href={`/article/${article.entry_id}`}>
            <h3 className="text-[15px] font-semibold leading-[1.45] text-gray-900 line-clamp-3 group-hover:text-blue-600 transition-colors duration-150 mb-2">
              {article.title}
            </h3>
          </Link>
        </ClickTracker>

        {/* Snippet */}
        {article.summary_snippet && (
          <p className="text-[13px] leading-[1.65] text-gray-500 line-clamp-2 mb-0">
            {article.summary_snippet}
          </p>
        )}

        {/* Scores — always at bottom */}
        <div className="mt-auto pt-4">
          <div className="border-t border-gray-50 pt-3 flex items-center gap-4">
            <ScorePill label="Cred"   score={article.credibility_score} softLabel={credibilitySoftLabel(article.credibility_score)} />
            <ScorePill label="Hype"   score={article.hype_score}        softLabel={hypeSoftLabel(article.hype_score)}        type="hype" />
            <ScorePill label="Impact" score={article.importance_score}  softLabel={importanceSoftLabel(article.importance_score)} />
          </div>
        </div>
      </div>
    </article>
  );
}
