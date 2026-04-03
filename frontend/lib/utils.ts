import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { formatDistanceToNow, parseISO } from "date-fns";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return "";
  try {
    return formatDistanceToNow(parseISO(dateStr), { addSuffix: true });
  } catch {
    return "";
  }
}

export function scoreColor(score: number | null | undefined): string {
  if (score == null) return "text-gray-400";
  if (score >= 0.7) return "text-green-600";
  if (score >= 0.4) return "text-yellow-600";
  return "text-red-500";
}

export function hypeColor(hype: number | null | undefined): string {
  if (hype == null) return "text-gray-400";
  if (hype <= 0.3) return "text-blue-600"; // low hype — underreported
  if (hype <= 0.6) return "text-yellow-600";
  return "text-orange-500"; // high hype — viral
}

export function scoreBar(score: number | null | undefined): number {
  if (score == null) return 0;
  return Math.round(score * 100);
}

// Category slug ↔ readable label helpers (mirrors the Python logic)
export function categorySlug(label: string): string {
  return label.toLowerCase().replace(/ & /g, "-").replace(/ /g, "-").replace(/&/g, "-");
}

export const CATEGORY_COLORS: Record<string, string> = {
  "AI & Machine Learning": "bg-violet-100 text-violet-800",
  "Cloud & Infrastructure": "bg-sky-100 text-sky-800",
  "Cybersecurity": "bg-red-100 text-red-800",
  "Mobile & Apps": "bg-green-100 text-green-800",
  "Data & Analytics": "bg-amber-100 text-amber-800",
  "Software Development": "bg-indigo-100 text-indigo-800",
  "Hardware & Devices": "bg-gray-100 text-gray-800",
  "Business & Startups": "bg-emerald-100 text-emerald-800",
  "General Tech": "bg-slate-100 text-slate-800",
};

// P6 — soft labels: signals not verdicts
export function hypeSoftLabel(score: number | null | undefined): string {
  if (score == null) return "";
  if (score <= 0.3) return "Low hype";
  if (score <= 0.6) return "Moderate hype";
  return "High hype risk";
}

export function credibilitySoftLabel(score: number | null | undefined): string {
  if (score == null) return "";
  if (score >= 0.7) return "High credibility";
  if (score >= 0.4) return "Moderate credibility";
  return "Needs verification";
}

export function importanceSoftLabel(score: number | null | undefined): string {
  if (score == null) return "";
  if (score >= 0.7) return "High impact";
  if (score >= 0.4) return "Moderate impact";
  return "Lower priority";
}
