import { api, NotFoundError } from "@/lib/api";
import type { CompiledStoryDetail, ArticleCard, StoryClaim } from "@/lib/types";
import Link from "next/link";
import { notFound } from "next/navigation";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ id: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  try {
    const story = await api.compiledStory(id);
    return { title: `${story.compiled_title ?? "Story"} — SmartNews` };
  } catch {
    return { title: "Story — SmartNews" };
  }
}

function parseJsonList(raw: string | null): string[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.map(String) : [];
  } catch {
    return raw.split(",").map((s) => s.trim()).filter(Boolean);
  }
}

function verdictUi(verdict: StoryClaim["verdict"]) {
  if (verdict === "DISPUTED") {
    return {
      label: "Disputed",
      box: "border-orange-200 bg-orange-50",
      badge: "bg-orange-100 text-orange-700",
    };
  }
  if (verdict === "CONSENSUS") {
    return {
      label: "Consensus",
      box: "border-green-200 bg-green-50",
      badge: "bg-green-100 text-green-700",
    };
  }
  return {
    label: "Single Source",
    box: "border-gray-200 bg-gray-50",
    badge: "bg-gray-100 text-gray-700",
  };
}

interface KeyClaim {
  claim: string;
  confirmed_by: string[];
  disputed_by: string[];
  confidence: number;
}

function parseKeyClaims(raw: string | null): KeyClaim[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function SourceArticleCard({ article }: { article: ArticleCard }) {
  return (
    <a
      href={article.link ?? "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded-lg border border-gray-200 p-4 hover:border-blue-300 hover:shadow-sm transition-all"
    >
      <p className="text-sm font-semibold text-gray-900 line-clamp-2 mb-1">
        {article.title}
      </p>
      <div className="flex items-center gap-2 text-xs text-gray-400">
        <span className="font-medium text-gray-600">{article.source_name}</span>
        {article.category && <span>· {article.category}</span>}
        {article.published_at && (
          <span>· {new Date(article.published_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}</span>
        )}
      </div>
    </a>
  );
}

export default async function StoryDetailPage({ params }: Props) {
  const { id } = await params;
  let story: CompiledStoryDetail;
  let claims: StoryClaim[] = [];
  try {
    story = await api.compiledStory(id);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    return (
      <div className="mx-auto max-w-3xl py-24 text-center">
        <p className="text-gray-500">Unable to load story. Try again later.</p>
        <Link href="/stories" className="mt-4 inline-block text-sm text-blue-600 hover:underline">
          ← Back to Stories
        </Link>
      </div>
    );
  }

  try {
    const claimResp = await api.storyClaims(id);
    claims = claimResp.items;
  } catch {
    claims = [];
  }

  const sources = parseJsonList(story.sources_used);
  const keyClaims = parseKeyClaims(story.key_claims);
  const consensusPoints = parseJsonList(story.consensus_points);
  const divergencePoints = parseJsonList(story.divergence_points);
  const hasPendingSummary = (story.compiled_summary ?? "").startsWith("AI synthesis pending")
    || (story.compiled_summary ?? "").startsWith("AI full synthesis is pending");
  const hasPendingBody = (story.compiled_body ?? "").startsWith("This story has been matched across multiple sources");

  return (
    <div className="mx-auto max-w-3xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <Link href="/stories" className="hover:text-blue-600 transition-colors">Multi-Source Stories</Link>
        <span>/</span>
        <span className="text-gray-600 line-clamp-1">{story.compiled_title ?? "Story"}</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-blue-100 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-blue-700">
            AI Synthesis
          </span>
          <span className="rounded-full bg-gray-100 px-3 py-0.5 text-xs font-semibold text-gray-600">
            {story.source_count ?? sources.length} sources
          </span>
          {story.category && (
            <span className="rounded-full bg-gray-100 px-3 py-0.5 text-xs text-gray-600">
              {story.category}
            </span>
          )}
        </div>
        <h1 className="text-2xl font-extrabold tracking-tight text-gray-900 leading-snug mb-3">
          {story.compiled_title}
        </h1>
        {story.last_published && (
          <p className="text-xs text-gray-400">
            Latest source: {formatDate(story.last_published)}
          </p>
        )}
      </header>

      {/* Summary */}
      {story.compiled_summary && !hasPendingSummary && (
        <div className="mb-6 rounded-xl bg-blue-50 border border-blue-100 p-5">
          <p className="text-sm font-semibold text-blue-800 uppercase tracking-wide mb-2">Summary</p>
          <p className="text-base text-gray-800 leading-relaxed">{story.compiled_summary}</p>
        </div>
      )}

      {hasPendingSummary && (
        <div className="mb-6 rounded-xl bg-amber-50 border border-amber-200 p-5">
          <p className="text-sm font-semibold text-amber-800 uppercase tracking-wide mb-2">Synthesis in progress</p>
          <p className="text-sm text-gray-700 leading-relaxed">
            This story match is new. Full synthesis and claim verification will appear after the next enrichment cycle.
          </p>
        </div>
      )}

      {/* Full compiled body */}
      {story.compiled_body && !hasPendingBody && (
        <article className="mb-8 prose prose-gray max-w-none">
          <div className="text-gray-800 leading-relaxed whitespace-pre-wrap text-[15px]">
            {story.compiled_body}
          </div>
        </article>
      )}

      {/* Key Claims */}
      {claims.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
            Claim Verification
          </h2>
          <div className="space-y-3">
            {claims.map((claim) => {
              const ui = verdictUi(claim.verdict);
              const confirming = parseJsonList(claim.sources_confirming);
              const disputing = parseJsonList(claim.sources_disputing);
              return (
                <div key={claim.claim_group_id} className={`rounded-lg border p-4 ${ui.box}`}>
                  <div className="mb-2 flex items-center gap-2">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ui.badge}`}>
                      {ui.label}
                    </span>
                    {claim.confidence != null && (
                      <span className="text-xs text-gray-500">
                        Confidence: {Math.round(claim.confidence * 100)}%
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-800 mb-2">{claim.claim_text}</p>
                  <div className="flex flex-wrap gap-2 text-xs">
                    {confirming.map((src) => (
                      <span key={`${claim.claim_group_id}-c-${src}`} className="rounded-full bg-green-100 px-2 py-0.5 text-green-700">
                        + {src}
                      </span>
                    ))}
                    {disputing.map((src) => (
                      <span key={`${claim.claim_group_id}-d-${src}`} className="rounded-full bg-orange-100 px-2 py-0.5 text-orange-700">
                        - {src}
                      </span>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* Key Claims (fallback from compiled payload) */}
      {claims.length === 0 && keyClaims.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
            Key Claims
          </h2>
          <div className="space-y-3">
            {keyClaims.map((claim, i) => (
              <div
                key={i}
                className={`rounded-lg border p-4 ${
                  claim.disputed_by.length > 0
                    ? "border-orange-200 bg-orange-50"
                    : "border-green-200 bg-green-50"
                }`}
              >
                <p className="text-sm text-gray-800 mb-2">{claim.claim}</p>
                <div className="flex flex-wrap gap-2 text-xs">
                  {claim.confirmed_by.map((src) => (
                    <span key={src} className="rounded-full bg-green-100 px-2 py-0.5 text-green-700">
                      ✓ {src}
                    </span>
                  ))}
                  {claim.disputed_by.map((src) => (
                    <span key={src} className="rounded-full bg-orange-100 px-2 py-0.5 text-orange-700">
                      ≠ {src}
                    </span>
                  ))}
                  <span className="text-gray-400 ml-auto">
                    Confidence: {Math.round((claim.confidence ?? 0) * 100)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Consensus & Divergence side by side */}
      {(consensusPoints.length > 0 || divergencePoints.length > 0) && (
        <div className="mb-8 grid gap-4 sm:grid-cols-2">
          {consensusPoints.length > 0 && (
            <section className="rounded-xl border border-green-200 bg-green-50 p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-green-700 mb-3">
                All sources agree
              </h2>
              <ul className="space-y-2">
                {consensusPoints.map((point, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-700">
                    <span className="text-green-500 shrink-0">✓</span>
                    {point}
                  </li>
                ))}
              </ul>
            </section>
          )}

          {divergencePoints.length > 0 && (
            <section className="rounded-xl border border-orange-200 bg-orange-50 p-4">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-orange-700 mb-3">
                Sources disagree
              </h2>
              <ul className="space-y-2">
                {divergencePoints.map((point, i) => (
                  <li key={i} className="flex gap-2 text-sm text-gray-700">
                    <span className="text-orange-500 shrink-0">≠</span>
                    {point}
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}

      {/* Source articles */}
      {story.source_articles.length > 0 && (
        <section className="mb-8">
          <h2 className="text-sm font-semibold uppercase tracking-wide text-gray-500 mb-3">
            Source Articles ({story.source_articles.length})
          </h2>
          <div className="space-y-2">
            {story.source_articles.map((article) => (
              <SourceArticleCard key={article.entry_id} article={article} />
            ))}
          </div>
        </section>
      )}

      {/* Disclaimer */}
      <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 text-xs text-gray-400">
        <strong>How this was compiled:</strong> Our AI read all source articles and synthesized the most complete, factual version. Every claim is attributed to its source. When sources conflict, both versions are shown. No facts were invented.
      </div>

      <div className="mt-6 text-center">
        <Link href="/stories" className="text-sm text-blue-600 hover:underline">
          ← All Multi-Source Stories
        </Link>
      </div>
    </div>
  );
}
