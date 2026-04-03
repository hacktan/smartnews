import { api } from "@/lib/api";
import type { NarrativeArc } from "@/lib/types";
import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Narrative Tracker — SmartNews" };

function HypeTrendBadge({ trend }: { trend: number | null }) {
  if (trend === null) return null;
  if (trend > 0.05)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700">
        ↑ Escalating
      </span>
    );
  if (trend < -0.05)
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700">
        ↓ Cooling
      </span>
    );
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
      → Stable
    </span>
  );
}

function ScoreDot({ value, color }: { value: number | null; color: string }) {
  if (value === null) return null;
  const pct = Math.round(value * 100);
  return (
    <span className={`text-xs font-semibold ${color}`}>{pct}%</span>
  );
}

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function ArcCard({ arc }: { arc: NarrativeArc }) {
  return (
    <Link
      href={`/narratives/${arc.arc_id}`}
      className="block rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <h2 className="text-base font-bold text-gray-900 leading-snug line-clamp-2">
          {arc.subtopic}
        </h2>
        <HypeTrendBadge trend={arc.hype_trend} />
      </div>

      {/* Latest headline */}
      {arc.latest_title && (
        <p className="text-sm text-gray-500 line-clamp-2 mb-3 leading-snug">
          {arc.latest_title}
        </p>
      )}

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-3 text-xs text-gray-400">
        {arc.category && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 font-medium">
            {arc.category}
          </span>
        )}
        <span>{arc.article_count} articles</span>
        {arc.span_days !== null && arc.span_days > 0 && (
          <span>over {arc.span_days}d</span>
        )}
        {arc.first_seen && arc.last_seen && (
          <span>
            {formatDate(arc.first_seen)} – {formatDate(arc.last_seen)}
          </span>
        )}
      </div>

      {/* Score strip */}
      <div className="mt-3 flex items-center gap-4 border-t border-gray-100 pt-3">
        <span className="text-xs text-gray-400">
          Imp <ScoreDot value={arc.avg_importance} color="text-blue-600" />
        </span>
        <span className="text-xs text-gray-400">
          Cred <ScoreDot value={arc.avg_credibility} color="text-green-600" />
        </span>
        <span className="text-xs text-gray-400">
          Hype <ScoreDot value={arc.avg_hype} color="text-orange-500" />
        </span>
      </div>
    </Link>
  );
}

export default async function NarrativesPage() {
  let data;
  try {
    data = await api.narratives(30);
  } catch {
    return (
      <div className="mx-auto max-w-3xl py-24 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Narrative Tracker</h1>
        <p className="text-gray-500 mb-2">Narratives not available yet.</p>
        <p className="text-xs text-gray-400">Run the pipeline to populate story arcs.</p>
        <Link href="/" className="mt-6 inline-block text-sm text-blue-600 hover:underline">← Back to Home</Link>
      </div>
    );
  }

  const arcs = data.items;

  // Split into escalating vs cooling vs stable for visual grouping
  const escalating = arcs.filter((a) => (a.hype_trend ?? 0) > 0.05);
  const cooling = arcs.filter((a) => (a.hype_trend ?? 0) < -0.05);
  const stable = arcs.filter(
    (a) => (a.hype_trend ?? 0) >= -0.05 && (a.hype_trend ?? 0) <= 0.05
  );

  return (
    <div className="mx-auto max-w-4xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <span className="text-gray-600">Narratives</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-purple-100 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-purple-700">
            Narrative Tracker
          </span>
          <span className="text-xs text-gray-400">{arcs.length} active story arcs</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          Stories in Motion
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          Groups of related articles showing how stories evolve — see what&apos;s escalating, cooling, or holding steady.
        </p>
      </header>

      {arcs.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 py-16 text-center text-gray-400">
          <p>No narrative arcs yet. Run the pipeline to detect evolving stories.</p>
        </div>
      ) : (
        <div className="space-y-10">
          {/* Escalating */}
          {escalating.length > 0 && (
            <section>
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-red-600">
                <span>↑ Escalating</span>
                <span className="rounded-full bg-red-100 px-2 py-0.5 text-xs">{escalating.length}</span>
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {escalating.map((arc) => <ArcCard key={arc.arc_id} arc={arc} />)}
              </div>
            </section>
          )}

          {/* Stable */}
          {stable.length > 0 && (
            <section>
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-gray-500">
                <span>→ Stable</span>
                <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs">{stable.length}</span>
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {stable.map((arc) => <ArcCard key={arc.arc_id} arc={arc} />)}
              </div>
            </section>
          )}

          {/* Cooling */}
          {cooling.length > 0 && (
            <section>
              <h2 className="mb-4 flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-green-600">
                <span>↓ Cooling Down</span>
                <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs">{cooling.length}</span>
              </h2>
              <div className="grid gap-4 sm:grid-cols-2">
                {cooling.map((arc) => <ArcCard key={arc.arc_id} arc={arc} />)}
              </div>
            </section>
          )}
        </div>
      )}

      <p className="mt-10 text-xs text-gray-400 text-center">
        Arcs group articles by AI-extracted subtopic · Updated every pipeline run · Scores are signals, not verdicts
      </p>
    </div>
  );
}
