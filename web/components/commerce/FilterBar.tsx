"use client";

import { useRouter, useSearchParams, usePathname } from "next/navigation";
import { useCallback, useState } from "react";
import { categories, allColours } from "@/lib/products";
import { cn } from "@/lib/cn";
import { IconChevronDown, IconClose } from "@/components/ui/icons";

export const SORTS = [
  { value: "featured", label: "Featured" },
  { value: "newest", label: "Newest" },
  { value: "popular", label: "Best selling" },
  { value: "price-asc", label: "Price, low to high" },
  { value: "price-desc", label: "Price, high to low" },
] as const;

const PRICE_BANDS = [
  { value: "0-100", label: "Under €100" },
  { value: "100-200", label: "€100 – €200" },
  { value: "200-400", label: "€200 – €400" },
  { value: "400-", label: "€400 and above" },
];

/**
 * Filters live entirely in the URL, so pages stay server-rendered, shareable
 * and back-button friendly. The rail and the toolbar are separate mounts that
 * both read and write the same params — no shared client state to sync.
 */
function useFilters() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const setParam = useCallback(
    (key: string, value: string | null) => {
      const next = new URLSearchParams(Array.from(params.entries()));
      if (value === null || next.get(key) === value) next.delete(key);
      else next.set(key, value);
      const qs = next.toString();
      router.push(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [params, pathname, router],
  );

  const active = {
    category: params.get("category"),
    colour: params.get("colour"),
    price: params.get("price"),
    sort: params.get("sort") ?? "featured",
  };

  return {
    setParam,
    active,
    count: [active.category, active.colour, active.price].filter(Boolean).length,
    clear: () => router.push(pathname, { scroll: false }),
  };
}

function FilterGroups({ compact = false }: { compact?: boolean }) {
  const { setParam, active, count, clear } = useFilters();

  return (
    <>
      <Group title="Category">
        <ul className={cn("flex gap-2", compact ? "flex-wrap" : "flex-col gap-1.5")}>
          {categories.map((c) => (
            <li key={c.slug}>
              <Chip
                compact={compact}
                active={active.category === c.slug}
                onClick={() => setParam("category", c.slug)}
              >
                {c.name}
              </Chip>
            </li>
          ))}
        </ul>
      </Group>

      <Group title="Colour">
        <ul className="flex flex-wrap gap-2.5">
          {allColours().map((c) => (
            <li key={c.slug}>
              <button
                type="button"
                onClick={() => setParam("colour", c.slug)}
                aria-pressed={active.colour === c.slug}
                title={c.name}
                className={cn(
                  "block h-7 w-7 rounded-full border transition-[box-shadow,border-color]",
                  active.colour === c.slug
                    ? "border-ink ring-1 ring-ink ring-offset-2 ring-offset-paper"
                    : "border-line-strong hover:border-ink",
                )}
                style={{ backgroundColor: c.hex }}
              >
                <span className="sr-only">{c.name}</span>
              </button>
            </li>
          ))}
        </ul>
      </Group>

      <Group title="Price">
        <ul className={cn("flex gap-2", compact ? "flex-wrap" : "flex-col gap-1.5")}>
          {PRICE_BANDS.map((b) => (
            <li key={b.value}>
              <Chip
                compact={compact}
                active={active.price === b.value}
                onClick={() => setParam("price", b.value)}
              >
                {b.label}
              </Chip>
            </li>
          ))}
        </ul>
      </Group>

      {count > 0 && (
        <button
          type="button"
          onClick={clear}
          className="label link-underline self-start text-muted hover:text-ink"
        >
          Clear all filters
        </button>
      )}
    </>
  );
}

/** Sidebar filters — desktop only. */
export function FilterRail() {
  return (
    <div className="flex flex-col gap-8">
      <FilterGroups />
    </div>
  );
}

/** Count, sort, and the mobile filter sheet. Sits above the grid. */
export function FilterToolbar({ total }: { total: number }) {
  const { setParam, active, count } = useFilters();
  const [open, setOpen] = useState(false);

  return (
    <>
      <div className="flex items-center justify-between gap-4 border-y border-line py-4">
        <p className="label text-muted">
          {total} {total === 1 ? "style" : "styles"}
        </p>

        <div className="flex items-center gap-6">
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="label flex items-center gap-2 lg:hidden"
          >
            Filter
            {count > 0 && <span className="text-muted">({count})</span>}
          </button>

          <div className="relative">
            <label htmlFor="sort" className="sr-only">
              Sort products
            </label>
            <select
              id="sort"
              value={active.sort}
              onChange={(e) => setParam("sort", e.target.value === "featured" ? null : e.target.value)}
              className="label cursor-pointer appearance-none bg-transparent py-1 pr-6 outline-none"
            >
              {SORTS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>
            <IconChevronDown className="pointer-events-none absolute top-1/2 right-0 -translate-y-1/2 text-muted" />
          </div>
        </div>
      </div>

      <div
        className={cn("fixed inset-0 z-[100] lg:hidden", open ? "visible" : "invisible")}
        aria-hidden={!open}
      >
        <div
          onClick={() => setOpen(false)}
          className={cn(
            "absolute inset-0 bg-ink/25 transition-opacity duration-[var(--duration-base)]",
            open ? "opacity-100" : "opacity-0",
          )}
        />
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Filters"
          className={cn(
            "absolute inset-x-0 bottom-0 max-h-[85dvh] overflow-y-auto bg-paper",
            "transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)]",
            open ? "translate-y-0" : "translate-y-full",
          )}
        >
          <div className="sticky top-0 z-10 flex items-center justify-between border-b border-line bg-paper px-5 py-4">
            <span className="label">Filter</span>
            <button type="button" onClick={() => setOpen(false)} className="-mr-2 p-2">
              <IconClose />
              <span className="sr-only">Close filters</span>
            </button>
          </div>
          <div className="flex flex-col gap-8 px-5 py-6">
            <FilterGroups compact />
          </div>
        </div>
      </div>
    </>
  );
}

function Group({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <h2 className="label text-faint">{title}</h2>
      {children}
    </div>
  );
}

function Chip({
  active,
  onClick,
  children,
  compact,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
  compact?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "label transition-colors duration-[var(--duration-quick)]",
        compact
          ? cn(
              "border px-3 py-2",
              active ? "border-ink bg-ink text-paper" : "border-line-strong text-ink-soft hover:border-ink",
            )
          : cn(
              "py-0.5 text-left",
              active ? "text-ink underline underline-offset-4" : "text-muted hover:text-ink",
            ),
      )}
    >
      {children}
    </button>
  );
}
