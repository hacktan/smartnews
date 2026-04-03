import type { TopicHistoryResponse } from "@/lib/types";

interface Props {
  history: TopicHistoryResponse;
}

export default function HypeHistoryChart({ history }: Props) {
  const { points, insufficient_data, latest_hype, latest_credibility, delta_hype_7d, delta_credibility_7d } = history;

  if (!points.length) {
    return (
      <div className="rounded-xl border border-gray-100 bg-white p-4 text-sm text-gray-500">
        No snapshot data yet for this topic.
      </div>
    );
  }

  if (insufficient_data) {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        Not enough reliable data yet. Trend lines activate after at least 2 daily snapshots
        with minimum 2 articles each.
      </div>
    );
  }

  const width = 760;
  const height = 260;
  const pad = 26;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;

  const x = (i: number) => pad + (i * innerW) / Math.max(1, points.length - 1);
  const y = (v: number | null | undefined) => {
    const safe = Math.max(0, Math.min(1, v ?? 0));
    return pad + (1 - safe) * innerH;
  };

  const line = (values: Array<number | null | undefined>) =>
    values.map((v, i) => `${x(i)},${y(v)}`).join(" ");

  const hypeLine = line(points.map((p) => p.avg_hype));
  const credibilityLine = line(points.map((p) => p.avg_credibility));

  const first = points[0];
  const last = points[points.length - 1];
  const fmt = (v: number | null | undefined) => (v == null ? "n/a" : v.toFixed(2));
  const fmtDelta = (v: number | null | undefined) =>
    v == null ? "n/a" : `${v >= 0 ? "+" : ""}${v.toFixed(2)}`;

  return (
    <div className="rounded-xl border border-gray-100 bg-white p-4 shadow-sm">
      <div className="mb-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div className="rounded-lg bg-orange-50 p-2">
          <p className="text-[11px] text-orange-700">Current Hype</p>
          <p className="text-sm font-semibold text-orange-900">{fmt(latest_hype)}</p>
        </div>
        <div className="rounded-lg bg-green-50 p-2">
          <p className="text-[11px] text-green-700">Current Credibility</p>
          <p className="text-sm font-semibold text-green-900">{fmt(latest_credibility)}</p>
        </div>
        <div className="rounded-lg bg-orange-50 p-2">
          <p className="text-[11px] text-orange-700">7d Hype Delta</p>
          <p className="text-sm font-semibold text-orange-900">{fmtDelta(delta_hype_7d)}</p>
        </div>
        <div className="rounded-lg bg-green-50 p-2">
          <p className="text-[11px] text-green-700">7d Credibility Delta</p>
          <p className="text-sm font-semibold text-green-900">{fmtDelta(delta_credibility_7d)}</p>
        </div>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-3 text-xs text-gray-600">
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-orange-500" /> Hype
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-2 w-2 rounded-full bg-green-600" /> Credibility
        </span>
        <span className="text-gray-400">{first.snapshot_date}</span>
        <span className="text-gray-400">to</span>
        <span className="text-gray-400">{last.snapshot_date}</span>
      </div>

      <svg viewBox={`0 0 ${width} ${height}`} className="h-52 w-full">
        <line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke="#e5e7eb" strokeWidth="1" />
        <line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke="#e5e7eb" strokeWidth="1" />

        <polyline fill="none" stroke="#f97316" strokeWidth="3" points={hypeLine} />
        <polyline fill="none" stroke="#16a34a" strokeWidth="3" points={credibilityLine} />
      </svg>
    </div>
  );
}
