"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ScoreBar } from "@/components/ScoreBadge";
import type { SourceLeaderboardItem } from "@/lib/types";

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "https://smartnews-api.onrender.com").replace(/\/$/, "");

type LoadState = "loading" | "ready" | "error";

export default function SourcesLeaderboardPage() {
  const [state, setState] = useState<LoadState>("loading");
  const [sources, setSources] = useState<SourceLeaderboardItem[]>([]);

  const load = async () => {
    setState("loading");
    try {
      const res = await fetch(`${API_BASE}/api/sources/leaderboard`, { cache: "no-store" });
      if (!res.ok) throw new Error(`status ${res.status}`);
      const data = await res.json();
      const rows = Array.isArray(data?.sources)
        ? data.sources.filter((s: unknown): s is SourceLeaderboardItem => Boolean(s && typeof s === "object"))
        : [];
      setSources(rows);
      setState("ready");
    } catch {
      setSources([]);
      setState("error");
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const safeSources = useMemo(
    () => sources.filter((s) => s && typeof s === "object"),
    [sources]
  );

  return (
    <div className="mx-auto max-w-3xl flex flex-col gap-8">
      <div>
        <p className="text-[11px] font-semibold tracking-widest uppercase text-blue-500 mb-1.5">Rankings</p>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">Source Leaderboard</h1>
        <p className="mt-1 text-sm text-gray-400">
          Ranked by average credibility score across analyzed articles
        </p>
      </div>

      {state === "error" && (
        <div className="rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
          Source rankings are temporarily unavailable. You can retry without leaving the page.
          <button
            onClick={() => void load()}
            className="ml-3 inline-flex rounded-md border border-amber-300 bg-white px-2.5 py-1 text-xs font-semibold text-amber-900 hover:bg-amber-100"
          >
            Retry
          </button>
        </div>
      )}

      <div className="rounded-2xl bg-white border border-gray-100 shadow-sm overflow-hidden">
        {state === "loading" ? (
          <div className="px-5 py-10 text-center text-sm text-gray-400">Loading source statistics...</div>
        ) : safeSources.length === 0 ? (
          <div className="px-5 py-10 text-center text-sm text-gray-400">No source statistics available yet.</div>
        ) : (
          safeSources.map((source, index) => (
            <div
              key={`${source.source_name ?? "unknown"}-${index}`}
              className="flex items-center gap-4 px-5 py-4 border-b border-gray-50 last:border-0 hover:bg-gray-50/60 transition-colors"
            >
              <span className="w-6 shrink-0 text-sm font-bold text-gray-300 text-right">{index + 1}</span>

              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-gray-900 truncate">{source.source_name ?? "Unknown source"}</p>
                <p className="text-[11px] text-gray-400 mt-0.5">{source.article_count} articles analyzed</p>
              </div>

              <div className="hidden sm:flex items-center gap-8 shrink-0">
                <div className="flex flex-col gap-1.5 w-28">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Credibility</span>
                    <span className="text-[11px] font-semibold text-green-600">
                      {source.avg_credibility != null ? (source.avg_credibility * 100).toFixed(0) + "%" : "-"}
                    </span>
                  </div>
                  <ScoreBar score={source.avg_credibility} />
                </div>
                <div className="flex flex-col gap-1.5 w-28">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-semibold uppercase tracking-wide text-gray-400">Hype</span>
                    <span className="text-[11px] font-semibold text-orange-500">
                      {source.avg_hype != null ? (source.avg_hype * 100).toFixed(0) + "%" : "-"}
                    </span>
                  </div>
                  <ScoreBar score={source.avg_hype} type="hype" />
                </div>
              </div>

              <div className="sm:hidden flex flex-col items-end gap-1 shrink-0 text-right">
                <span className="text-[11px] text-gray-500">
                  Cred <span className="font-semibold text-green-600">{source.avg_credibility != null ? (source.avg_credibility * 100).toFixed(0) + "%" : "-"}</span>
                </span>
                <span className="text-[11px] text-gray-500">
                  Hype <span className="font-semibold text-orange-500">{source.avg_hype != null ? (source.avg_hype * 100).toFixed(0) + "%" : "-"}</span>
                </span>
              </div>
            </div>
          ))
        )}
      </div>

      <p className="text-xs text-gray-400 text-center">
        Scores are AI-generated signals | Updated every pipeline run | Not editorial verdicts
      </p>

      <p className="text-center">
        <Link href="/" className="text-sm text-blue-600 hover:underline">Back to Home</Link>
      </p>
    </div>
  );
}
