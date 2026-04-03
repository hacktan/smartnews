import { cn, CATEGORY_COLORS } from "@/lib/utils";

interface Props {
  category: string | null | undefined;
  className?: string;
}

export default function CategoryBadge({ category, className }: Props) {
  if (!category) return null;
  const color = CATEGORY_COLORS[category] ?? "bg-slate-100 text-slate-800";
  return (
    <span className={cn("inline-block rounded-full px-2 py-0.5 text-xs font-medium", color, className)}>
      {category}
    </span>
  );
}
