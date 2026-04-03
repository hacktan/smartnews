"use client";
import { useState, useEffect } from "react";
import Link from "next/link";

interface Props {
  categories: { slug: string; label: string }[];
}

const NAV_LINKS = [
  { href: "/", label: "Home" },
  { href: "/briefing", label: "Daily Briefing" },
  { href: "/stories", label: "Multi-Source Stories" },
  { href: "/narratives", label: "Narratives" },
  { href: "/sources", label: "Sources" },
  { href: "/search", label: "Search" },
];

export default function MobileNav({ categories }: Props) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    document.body.style.overflow = open ? "hidden" : "";
    return () => { document.body.style.overflow = ""; };
  }, [open]);

  const close = () => setOpen(false);

  return (
    <>
      {/* Hamburger — mobile only */}
      <button
        className="sm:hidden flex items-center justify-center w-9 h-9 rounded-xl text-gray-500 hover:bg-gray-100 transition-colors shrink-0"
        onClick={() => setOpen(true)}
        aria-label="Open menu"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
          <line x1="3" y1="6" x2="21" y2="6" />
          <line x1="3" y1="12" x2="21" y2="12" />
          <line x1="3" y1="18" x2="21" y2="18" />
        </svg>
      </button>

      {/* Backdrop */}
      {open && (
        <div
          onClick={close}
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(0,0,0,0.4)",
            zIndex: 998,
          }}
        />
      )}

      {/* Drawer */}
      {open && (
        <div
          style={{
            position: "fixed",
            top: 0,
            right: 0,
            bottom: 0,
            width: "min(300px, 88vw)",
            backgroundColor: "#ffffff",
            zIndex: 999,
            display: "flex",
            flexDirection: "column",
            overflowY: "auto",
            boxShadow: "-8px 0 40px rgba(0,0,0,0.12)",
          }}
        >
          {/* Header */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "18px 20px",
            borderBottom: "1px solid #f3f4f6",
            flexShrink: 0,
          }}>
            <span style={{ fontWeight: 900, fontSize: "17px", letterSpacing: "-0.02em" }}>
              <span style={{ color: "#2563eb" }}>Smart</span>
              <span style={{ color: "#111827" }}>News</span>
            </span>
            <button
              onClick={close}
              aria-label="Close menu"
              style={{
                width: 34, height: 34,
                display: "flex", alignItems: "center", justifyContent: "center",
                borderRadius: 10, color: "#6b7280",
                border: "none", background: "#f9fafb", cursor: "pointer",
              }}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <line x1="18" y1="6" x2="6" y2="18" />
                <line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>

          {/* Nav links */}
          <div style={{ display: "flex", flexDirection: "column", padding: "6px 0" }}>
            {NAV_LINKS.map((item) => (
              <Link
                key={item.href}
                href={item.href}
                onClick={close}
                style={{
                  padding: "14px 20px",
                  fontSize: "15px",
                  fontWeight: 500,
                  color: "#1f2937",
                  textDecoration: "none",
                  display: "block",
                  borderBottom: "1px solid #f9fafb",
                }}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* Categories */}
          {categories.length > 0 && (
            <div style={{ padding: "20px", borderTop: "1px solid #f3f4f6", marginTop: 4 }}>
              <p style={{
                fontSize: "10px", fontWeight: 700, color: "#9ca3af",
                textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "12px",
              }}>
                Categories
              </p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
                {categories.map((c) => (
                  <Link
                    key={c.slug}
                    href={`/category/${c.slug}`}
                    onClick={close}
                    style={{
                      borderRadius: "9999px",
                      backgroundColor: "#f3f4f6",
                      padding: "6px 13px",
                      fontSize: "12px",
                      fontWeight: 500,
                      color: "#374151",
                      textDecoration: "none",
                    }}
                  >
                    {c.label}
                  </Link>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </>
  );
}
