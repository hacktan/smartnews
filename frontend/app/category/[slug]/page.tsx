import { api, NotFoundError } from "@/lib/api";
import ArticleCard from "@/components/ArticleCard";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import Link from "next/link";

export const dynamic = "force-dynamic";

interface Props {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const label = slug.replace(/-/g, " ");
  return { title: `${label} — SmartNews` };
}

export default async function CategoryPage({ params, searchParams }: Props) {
  const { slug } = await params;
  const { page: pageStr } = await searchParams;
  const page = Math.max(1, parseInt(pageStr ?? "1", 10));

  let feed;
  try {
    feed = await api.categoryFeed(slug, page, 20);
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

  const totalPages = Math.ceil(feed.total / feed.page_size);

  return (
    <div className="flex flex-col gap-8">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-2 text-sm text-gray-400">
        <Link href="/" className="hover:text-blue-600 transition-colors">Home</Link>
        <span>/</span>
        <span className="text-gray-600">{feed.category}</span>
      </nav>

      {/* Header */}
      <div>
        <p className="text-[11px] font-semibold tracking-widest uppercase text-blue-500 mb-1.5">Category</p>
        <h1 className="text-3xl font-extrabold tracking-tight text-gray-900">
          {feed.category}
        </h1>
        <p className="mt-1 text-sm text-gray-500">
          {feed.total} articles · page {feed.page} of {totalPages}
        </p>
      </div>

      {/* Grid */}
      {feed.items.length === 0 ? (
        <p className="text-gray-400">No articles found.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {feed.items.map((a) => (
            <ArticleCard
              key={a.entry_id}
              article={{
                entry_id: a.entry_id,
                title: a.title,
                source_name: a.source_name ?? "",
                published_at: a.published_at,
                category: a.category,
                summary_snippet: a.summary_snippet,
                hype_score: a.hype_score,
                credibility_score: a.credibility_score,
                importance_score: a.importance_score,
                link: null,
                publish_date: null,
                image_url: a.image_url ?? null,
              }}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <nav className="flex items-center justify-center gap-2">
          {page > 1 && (
            <a
              href={`/category/${slug}?page=${page - 1}`}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              ← Previous
            </a>
          )}
          <span className="text-sm text-gray-500">
            {page} / {totalPages}
          </span>
          {page < totalPages && (
            <a
              href={`/category/${slug}?page=${page + 1}`}
              className="rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Next →
            </a>
          )}
        </nav>
      )}
    </div>
  );
}
