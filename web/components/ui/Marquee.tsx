import { cn } from "@/lib/cn";

/**
 * Seamless ticker. The list is rendered twice and translated by -50%, so the
 * loop has no visible seam; the duplicate is hidden from assistive tech.
 */
export function Marquee({
  items,
  className,
  separator = "—",
}: {
  items: string[];
  className?: string;
  separator?: string;
}) {
  const run = (hidden: boolean) => (
    <ul
      aria-hidden={hidden || undefined}
      className="flex shrink-0 items-center gap-10 pr-10 sm:gap-16 sm:pr-16"
    >
      {items.map((item, i) => (
        <li key={`${item}-${i}`} className="flex items-center gap-10 sm:gap-16">
          <span className="label whitespace-nowrap">{item}</span>
          <span aria-hidden className="opacity-40">
            {separator}
          </span>
        </li>
      ))}
    </ul>
  );

  return (
    <div className={cn("group relative overflow-hidden", className)}>
      <div className="flex w-max animate-[var(--animate-marquee)] group-hover:[animation-play-state:paused]">
        {run(false)}
        {run(true)}
      </div>
    </div>
  );
}
