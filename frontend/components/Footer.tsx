import Link from "next/link";

const FOOTER_LINKS = [
  { href: "/briefing", label: "Daily Briefing" },
  { href: "/stories", label: "Multi-Source" },
  { href: "/narratives", label: "Narratives" },
  { href: "/sources", label: "Sources" },
  { href: "/search", label: "Search" },
];

export default function Footer() {
  return (
    <footer className="mt-16 border-t border-gray-100 bg-white">
      <div className="mx-auto max-w-7xl px-4 py-8">
        <div className="flex flex-col items-center gap-4 sm:flex-row sm:justify-between">
          {/* Brand */}
          <div className="text-center sm:text-left">
            <span className="text-[15px] font-black tracking-tight">
              <span className="text-blue-600">Smart</span>
              <span className="text-gray-900">News</span>
            </span>
            <p className="mt-0.5 text-xs text-gray-400">
              AI-curated tech news · DuckDB pipeline + GPT-4o-mini
            </p>
          </div>

          {/* Quick links */}
          <nav className="flex flex-wrap justify-center gap-x-5 gap-y-1.5">
            {FOOTER_LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-xs text-gray-400 hover:text-blue-600 transition-colors"
              >
                {l.label}
              </Link>
            ))}
          </nav>

          {/* Meta */}
          <div className="text-xs text-gray-400 text-center sm:text-right">
            <a
              href="https://github.com/hacktan/smartnews"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-blue-600 transition-colors"
            >
              GitHub
            </a>
            <span className="mx-2">·</span>
            <span>Scores are signals, not verdicts</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
