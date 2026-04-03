import { api } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import SearchBar from "@/components/SearchBar";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";

interface Props {
  searchParams: Promise<{
    q?: string;
    category?: string;
    source?: string;
    days?: string;
    min_credibility?: string;
    max_hype?: string;
    min_importance?: string;
  }>;
}

export async function generateMetadata({ searchParams }: Props): Promise<Metadata> {
  const { q } = await searchParams;
  return { title: q ? `"${q}" — SmartNews Search` : "Search — SmartNews" };
}

const DAY_OPTIONS = [
  { label: "Any time", value: "" },
  { label: "Last 24h", value: "1" },
  { label: "Last 7 days", value: "7" },
  { label: "Last 30 days", value: "30" },
];

export default async function SearchPage({ searchParams }: Props) {
  const { q, category, source, days, min_credibility, max_hype, min_importance } = await searchParams;

  let results = null;
  let error = "";
  if (q) {
    try {
      results = await api.search(q, {
        category: category || undefined,
        source: source || undefined,
        days: days ? parseInt(days, 10) : undefined,
        min_credibility: min_credibility ? parseFloat(min_credibility) : undefined,
        max_hype: max_hype ? parseFloat(max_hype) : undefined,
        min_importance: min_importance ? parseFloat(min_importance) : undefined,
      });
    } catch (e) {
      error = "Search failed. Please try again.";
    }
  }

  return (
    <div className="mx-auto max-w-4xl flex flex-col gap-8">
      {/* Search form */}
      <div>
        <h1 className="mb-4 text-2xl font-extrabold tracking-tight text-gray-900">Search</h1>
        <SearchBar defaultValue={q ?? ""} autoFocus />

        {/* Filter row */}
        <form method="GET" action="/search" className="mt-4 flex flex-wrap items-center gap-3">
          <input type="hidden" name="q" value={q ?? ""} />

          <select
            name="days"
            defaultValue={days ?? ""}
            className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-700"
          >
            {DAY_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>

          {source && (
            <span className="flex items-center gap-1 rounded-full bg-gray-100 px-3 py-1 text-xs font-medium text-gray-600">
              Source: {source}
              <a href={`/search?q=${encodeURIComponent(q ?? "")}`} className="ml-1 hover:text-red-500">×</a>
            </span>
          )}

          {q && (
            <button
              type="submit"
              className="rounded-lg bg-gray-100 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-200 transition"
            >
              Apply filters
            </button>
          )}
        </form>

        {q && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-gray-500 mr-2">Smart Filters:</span>
            <a href={`/search?q=${encodeURIComponent(q)}&min_credibility=0.7&max_hype=0.3`} className="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-800 hover:bg-blue-200 transition">
              Verified Signal
            </a>
            <a href={`/search?q=${encodeURIComponent(q)}&min_importance=0.7`} className="rounded-full bg-purple-100 px-3 py-1 text-xs font-medium text-purple-800 hover:bg-purple-200 transition">
              Breaking & Bold
            </a>
            <a href={`/search?q=${encodeURIComponent(q)}&min_credibility=0.7&min_importance=0.5`} className="rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-800 hover:bg-green-200 transition">
              Deep Analysis
            </a>
            <a href={`/search?q=${encodeURIComponent(q)}&max_hype=0.25`} className="rounded-full bg-yellow-100 px-3 py-1 text-xs font-medium text-yellow-800 hover:bg-yellow-200 transition">
              Low Hype
            </a>
          </div>
        )}
      </div>

      {/* Results */}
      {error && <p className="text-red-500">{error}</p>}

      {results && (
        <div className="flex flex-col gap-4">
          <p className="text-sm text-gray-500">
            {results.total} result{results.total !== 1 ? "s" : ""} for{" "}
            <strong>&quot;{results.query}&quot;</strong>
          </p>

          {results.items.length === 0 ? (
            <p className="text-gray-400">No articles matched your search.</p>
          ) : (
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              {results.items.map((a) => (
                <ArticleCard key={a.entry_id} article={a} />
              ))}
            </div>
          )}
        </div>
      )}

      {!q && (
        <div className="rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
          <p className="text-sm font-medium text-gray-600 mb-3">Try searching for:</p>
          <div className="flex flex-wrap gap-2">
            {["AI safety", "cloud computing", "cybersecurity", "iPhone", "ChatGPT", "data breach", "startup funding", "open source"].map((term) => (
              <a
                key={term}
                href={`/search?q=${encodeURIComponent(term)}`}
                className="rounded-full bg-gray-100 px-3 py-1.5 text-sm text-gray-700 hover:bg-blue-100 hover:text-blue-700 transition-colors"
              >
                {term}
              </a>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
