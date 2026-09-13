"use client";

import { useId, useState } from "react";
import { cn } from "@/lib/cn";

export type AccordionItem = {
  title: string;
  content: React.ReactNode;
};

export function Accordion({
  items,
  defaultOpen,
  className,
  headingLevel = 3,
}: {
  items: AccordionItem[];
  /** Index of the panel open on first paint, if any. */
  defaultOpen?: number;
  className?: string;
  /** Match the surrounding outline so screen readers get no level jump. */
  headingLevel?: 2 | 3 | 4;
}) {
  const Heading = `h${headingLevel}` as "h2" | "h3" | "h4";
  const [open, setOpen] = useState<number | null>(defaultOpen ?? null);
  const id = useId();

  return (
    <div className={cn("border-t border-line", className)}>
      {items.map((item, i) => {
        const expanded = open === i;
        return (
          <div key={item.title} className="border-b border-line">
            <Heading>
              <button
                type="button"
                aria-expanded={expanded}
                aria-controls={`${id}-panel-${i}`}
                id={`${id}-trigger-${i}`}
                onClick={() => setOpen(expanded ? null : i)}
                className="group flex w-full items-center justify-between gap-6 py-5 text-left"
              >
                <span className="label">{item.title}</span>
                <span
                  aria-hidden
                  className="relative h-3 w-3 shrink-0 text-muted transition-colors group-hover:text-ink"
                >
                  <span className="absolute top-1/2 left-0 h-px w-3 -translate-y-1/2 bg-current" />
                  <span
                    className={cn(
                      "absolute top-1/2 left-0 h-px w-3 -translate-y-1/2 bg-current",
                      "transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)]",
                      expanded ? "rotate-0" : "rotate-90",
                    )}
                  />
                </span>
              </button>
            </Heading>
            <div
              id={`${id}-panel-${i}`}
              role="region"
              aria-labelledby={`${id}-trigger-${i}`}
              hidden={!expanded}
              className="pb-6"
            >
              <div className="max-w-prose text-[0.9375rem] leading-relaxed text-ink-soft">
                {item.content}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
