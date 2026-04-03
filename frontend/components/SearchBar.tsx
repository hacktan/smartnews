"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";

interface Props {
  defaultValue?: string;
  autoFocus?: boolean;
}

export default function SearchBar({ defaultValue = "", autoFocus = false }: Props) {
  const router = useRouter();
  const [q, setQ] = useState(defaultValue);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = q.trim();
    if (trimmed) router.push(`/search?q=${encodeURIComponent(trimmed)}`);
  }

  return (
    <form onSubmit={handleSubmit} className="flex w-full">
      <input
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder="Search…"
        autoFocus={autoFocus}
        className="flex-1 min-w-0 rounded-l-xl border border-gray-200 bg-white px-3 py-2 text-sm text-gray-900 placeholder-gray-400 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
      />
      <button
        type="submit"
        aria-label="Search"
        className="rounded-r-xl bg-blue-600 px-3 sm:px-5 py-2 text-sm font-semibold text-white transition hover:bg-blue-700 active:bg-blue-800 shrink-0"
      >
        <svg className="sm:hidden" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
        <span className="hidden sm:inline">Search</span>
      </button>
    </form>
  );
}
