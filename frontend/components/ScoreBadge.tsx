import { cn, scoreColor, hypeColor, scoreBar } from "@/lib/utils";

interface ScorePillProps {
  label: string;
  score: number | null | undefined;
  type?: "default" | "hype";
  softLabel?: string;
  className?: string;
}

export function ScorePill({ label, score, type = "default", softLabel, className }: ScorePillProps) {
  if (score == null) return null;
  const color = type === "hype" ? hypeColor(score) : scoreColor(score);
  return (
    <span className={cn("inline-flex items-baseline gap-1", className)}>
      <span className="text-[10px] font-medium text-gray-400 tracking-wide uppercase">{label}</span>
      <span className={cn("text-[11px] font-semibold", color)}>
        {softLabel ?? `${scoreBar(score)}%`}
      </span>
    </span>
  );
}

interface ScoreBarProps {
  score: number | null | undefined;
  type?: "default" | "hype";
  className?: string;
}

export function ScoreBar({ score, type = "default", className }: ScoreBarProps) {
  if (score == null) return null;
  const pct = scoreBar(score);
  const barColor =
    type === "hype"
      ? score <= 0.3 ? "bg-blue-400" : score <= 0.6 ? "bg-amber-400" : "bg-orange-400"
      : score >= 0.7 ? "bg-emerald-400" : score >= 0.4 ? "bg-amber-400" : "bg-red-400";

  return (
    <div className={cn("h-1 w-full rounded-full bg-gray-100", className)}>
      <div className={cn("h-1 rounded-full transition-all", barColor)} style={{ width: `${pct}%` }} />
    </div>
  );
}
