"use client";

import { useEffect, useRef, useState } from "react";
import { cn } from "@/lib/cn";

type Props = {
  children: React.ReactNode;
  className?: string;
  /** Stagger, in milliseconds. */
  delay?: number;
  /** How much of the element must be visible before it reveals. */
  threshold?: number;
  as?: "div" | "section" | "li" | "article" | "span";
};

/**
 * Reveals children once they scroll into view.
 *
 * The element is visible by default in CSS when JS has not run, so nothing
 * here is load-bearing for reading the page — it only adds the entrance.
 * `prefers-reduced-motion` is handled in globals.css.
 */
export function Reveal({
  children,
  className,
  delay = 0,
  threshold = 0.15,
  as: Tag = "div",
}: Props) {
  const ref = useRef<HTMLElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || revealed) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold, rootMargin: "0px 0px -8% 0px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [revealed, threshold]);

  return (
    <Tag
      // @ts-expect-error — one ref type across the union of tags
      ref={ref}
      data-reveal=""
      data-revealed={revealed ? "true" : "false"}
      style={{ "--reveal-delay": `${delay}ms` } as React.CSSProperties}
      className={cn(className)}
    >
      {children}
    </Tag>
  );
}
