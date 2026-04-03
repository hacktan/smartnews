"use client";

/**
 * ClickTracker — fires POST /api/events/click fire-and-forget.
 * Server-side rendered pages (ArticleCard, etc.) wrap links with this component.
 * On click it calls the events API then navigates normally.
 */

const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://smartnews-api.victorioussea-ab137c42.eastus.azurecontainerapps.io";

interface Props {
  entryId: string;
  source?: string;
  className?: string;
  children: React.ReactNode;
}

export default function ClickTracker({ entryId, source, className, children }: Props) {
  function handleClick() {
    // Fire-and-forget — never block navigation or throw
    try {
      fetch(`${API_BASE}/api/events/click`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ entry_id: entryId, source: source ?? "card" }),
        keepalive: true,
      }).catch(() => {});
    } catch {
      // swallow all errors — tracking must never break UX
    }
  }

  return (
    <span className={className} onClick={handleClick}>
      {children}
    </span>
  );
}
