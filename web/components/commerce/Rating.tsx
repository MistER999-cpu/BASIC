import { IconStar } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

export function Rating({
  value,
  count,
  className,
  showCount = true,
}: {
  value: number;
  count: number;
  className?: string;
  showCount?: boolean;
}) {
  const rounded = Math.round(value);
  return (
    <span className={cn("inline-flex items-center gap-2", className)}>
      <span className="flex items-center gap-0.5 text-ink" aria-hidden>
        {[1, 2, 3, 4, 5].map((i) => (
          <IconStar key={i} className={i <= rounded ? "opacity-100" : "opacity-20"} />
        ))}
      </span>
      <span className="label text-muted">
        {value.toFixed(1)}
        {showCount && ` · ${count} reviews`}
      </span>
      <span className="sr-only">
        Rated {value.toFixed(1)} out of 5 from {count} reviews
      </span>
    </span>
  );
}
