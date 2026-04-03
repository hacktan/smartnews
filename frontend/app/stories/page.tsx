import { api } from "@/lib/api";
import type { CompiledStory } from "@/lib/types";
import Link from "next/link";
import type { Metadata } from "next";

export const dynamic = "force-dynamic";
export const metadata: Metadata = { title: "Multi-Source Stories — SmartNews" };

function formatDate(iso: string | null) {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
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

function StoryCard({ story }: { story: CompiledStory }) {
  const sources = parseJsonList(story.sources_used);

  return (
    <Link
      href={`/story/${story.story_id}`}
      className="block rounded-xl border border-gray-200 bg-white p-5 hover:border-blue-300 hover:shadow-md transition-all"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <h2 className="text-base font-bold text-gray-900 leading-snug line-clamp-2">
          {story.compiled_title || "Untitled Story"}
        </h2>
        <span className="shrink-0 inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-semibold text-blue-700">
          {story.source_count ?? sources.length} sources
        </span>
      </div>

      {/* Summary */}
      {story.compiled_summary && (
        <p className="text-sm text-gray-600 line-clamp-3 mb-3 leading-relaxed">
          {story.compiled_summary}
        </p>
      )}

      {/* Sources */}
      {sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {sources.slice(0, 5).map((src) => (
            <span
              key={src}
              className="rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600"
            >
              {src}
            </span>
          ))}
        </div>
      )}

      {/* Meta */}
      <div className="flex items-center gap-3 text-xs text-gray-400 border-t border-gray-100 pt-3">
        {story.category && (
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-gray-600 font-medium">
            {story.category}
          </span>
        )}
        {story.last_published && (
          <span>Latest: {formatDate(story.last_published)}</span>
        )}
        <span className="ml-auto text-blue-500 font-medium">Read full synthesis →</span>
      </div>
    </Link>
  );
}

export default async function StoriesPage() {
  let data;
  try {
    data = await api.compiledStories(30);
  } catch {
    return (
      <div className="mx-auto max-w-3xl py-24 text-center">
        <h1 className="text-2xl font-bold text-gray-900 mb-3">Multi-Source Stories</h1>
        <p className="text-gray-500 mb-2">No compiled stories available yet.</p>
        <p className="text-xs text-gray-400">
          Stories are compiled when multiple sources cover the same event. Run the pipeline to generate compilations.
        </p>
        <Link href="/" className="mt-6 inline-block text-sm text-blue-600 hover:underline">
          ← Back to Home
        </Link>
      </div>
    );
  }

  const stories = data.items;

  return (
    <div className="mx-auto max-w-4xl">
      {/* Breadcrumb */}
      <nav className="mb-6 flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <span className="text-gray-600">Multi-Source Stories</span>
      </nav>

      {/* Header */}
      <header className="mb-8">
        <div className="mb-2 flex items-center gap-2">
          <span className="rounded-full bg-blue-100 px-3 py-0.5 text-xs font-semibold uppercase tracking-wide text-blue-700">
            AI Synthesis
          </span>
          <span className="text-xs text-gray-400">{stories.length} compiled stories</span>
        </div>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          Multi-Source Stories
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          When multiple outlets cover the same story, our AI reads every version and compiles the most complete, accurate account — attributing unique details to each source.
        </p>
      </header>

      {stories.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 py-16 text-center text-gray-400">
          <p className="font-medium mb-1">No compiled stories yet</p>
          <p className="text-xs">
            Compilations appear after multiple sources cover the same event within 48 hours.
          </p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {stories.map((story) => (
            <StoryCard key={story.story_id} story={story} />
          ))}
        </div>
      )}

      <p className="mt-10 text-xs text-gray-400 text-center">
        AI-compiled from multiple verified sources · Claims are attributed, not invented · Updated every pipeline run
      </p>
    </div>
  );
}
