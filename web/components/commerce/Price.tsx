import { formatPrice } from "@/lib/format";
import { cn } from "@/lib/cn";

export function Price({
  amount,
  compareAt,
  className,
}: {
  amount: number;
  compareAt?: number;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-baseline gap-2 tabular-nums", className)}>
      <span>{formatPrice(amount)}</span>
      {compareAt && compareAt > amount && (
        <>
          <span className="text-faint line-through">{formatPrice(compareAt)}</span>
          <span className="sr-only">reduced from {formatPrice(compareAt)}</span>
        </>
      )}
    </span>
  );
}
