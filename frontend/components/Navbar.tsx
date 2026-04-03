import Link from "next/link";
import { api } from "@/lib/api";
import SearchBar from "./SearchBar";
import MobileNav from "./MobileNav";

export default async function Navbar() {
  let categories: { slug: string; label: string }[] = [];
  try {
    const data = await api.categories();
    categories = data.categories.slice(0, 8);
  } catch {
    // fail silently — nav still renders without categories
  }

  return (
    <header className="sticky top-0 z-40 bg-white/80 backdrop-blur-xl border-b border-gray-100/80">
      <div className="mx-auto max-w-7xl px-4">
        {/* Top bar */}
        <div className="flex h-[52px] items-center gap-4">
          {/* Logo */}
          <Link href="/" className="flex items-center shrink-0 mr-1">
            <span className="text-[19px] font-black tracking-tight text-blue-600">Smart</span>
            <span className="text-[19px] font-black tracking-tight text-gray-900">News</span>
          </Link>

          {/* Search */}
          <div className="flex-1 min-w-0">
            <SearchBar />
          </div>

          {/* Desktop nav links */}
          <nav className="hidden sm:flex items-center gap-1 shrink-0">
            <Link
              href="/briefing"
              className="px-3 py-1.5 rounded-full text-[13px] font-medium text-blue-600 hover:bg-blue-50 transition-colors"
            >
              Briefing
            </Link>
            <Link
              href="/stories"
              className="px-3 py-1.5 rounded-full text-[13px] font-medium text-emerald-600 hover:bg-emerald-50 transition-colors"
            >
              Multi-Source
            </Link>
            <Link
              href="/narratives"
              className="px-3 py-1.5 rounded-full text-[13px] text-purple-600 hover:bg-purple-50 transition-colors font-medium"
            >
              Narratives
            </Link>
            <Link
              href="/sources"
              className="px-3 py-1.5 rounded-full text-[13px] text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors"
            >
              Sources
            </Link>
            <Link
              href="/search"
              className="px-3 py-1.5 rounded-full text-[13px] text-gray-500 hover:text-gray-900 hover:bg-gray-50 transition-colors"
            >
              Search
            </Link>
          </nav>

          {/* Mobile hamburger */}
          <MobileNav categories={categories} />
        </div>

        {/* Category strip — desktop only */}
        {categories.length > 0 && (
          <nav className="hidden sm:flex items-center gap-0.5 overflow-x-auto pb-2 scrollbar-hide">
            {categories.map((c) => (
              <Link
                key={c.slug}
                href={`/category/${c.slug}`}
                className="shrink-0 rounded-full px-3 py-1 text-[12px] font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-900 transition-colors"
              >
                {c.label}
              </Link>
            ))}
          </nav>
        )}
      </div>
    </header>
  );
}
