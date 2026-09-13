"use client";

import { IconMinus, IconPlus } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

export function QuantityStepper({
  value,
  onChange,
  min = 1,
  max = 10,
  label = "Quantity",
  className,
}: {
  value: number;
  onChange: (next: number) => void;
  min?: number;
  max?: number;
  label?: string;
  className?: string;
}) {
  return (
    <div className={cn("inline-flex items-center border border-line-strong", className)}>
      <button
        type="button"
        onClick={() => onChange(Math.max(min, value - 1))}
        disabled={value <= min}
        className="flex h-11 w-11 items-center justify-center text-muted transition-colors hover:text-ink disabled:opacity-30"
      >
        <IconMinus />
        <span className="sr-only">Decrease {label.toLowerCase()}</span>
      </button>
      <span aria-live="polite" className="w-8 text-center text-sm tabular-nums">
        {value}
      </span>
      <button
        type="button"
        onClick={() => onChange(Math.min(max, value + 1))}
        disabled={value >= max}
        className="flex h-11 w-11 items-center justify-center text-muted transition-colors hover:text-ink disabled:opacity-30"
      >
        <IconPlus />
        <span className="sr-only">Increase {label.toLowerCase()}</span>
      </button>
    </div>
  );
}
