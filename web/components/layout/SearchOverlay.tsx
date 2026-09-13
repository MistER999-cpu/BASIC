"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";
import { searchProducts, products } from "@/lib/products";
import { formatPrice } from "@/lib/format";
import { useStore } from "@/components/providers/StoreProvider";
import { Overlay } from "@/components/ui/Overlay";
import { IconSearch } from "@/components/ui/icons";

const SUGGESTIONS = ["Rib series", "Merino", "Trousers", "Outerwear", "Accessories"];

export function SearchOverlay() {
  const { searchOpen, setSearchOpen } = useStore();
  const [query, setQuery] = useState("");
  const router = useRouter();

  const results = useMemo(() => searchProducts(query).slice(0, 6), [query]);
  const popular = useMemo(
    () => [...products].sort((a, b) => b.popularity - a.popularity).slice(0, 4),
    [],
  );
  const shown = query.trim() ? results : popular;

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setSearchOpen(false);
    router.push(`/search?q=${encodeURIComponent(query.trim())}`);
  }

  return (
    <Overlay
      open={searchOpen}
      onClose={() => setSearchOpen(false)}
      label="Search"
      title="Search"
      side="top"
      className="max-h-[90dvh]"
    >
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
          <form onSubmit={onSubmit}>
            <label htmlFor="site-search" className="sr-only">
              Search products
            </label>
            <div className="flex items-center gap-4 border-b border-ink pb-4">
              <IconSearch className="shrink-0 text-muted" width={20} height={20} />
              <input
                id="site-search"
                type="search"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What are you looking for?"
                autoComplete="off"
                className="font-display w-full bg-transparent text-2xl outline-none placeholder:text-faint sm:text-3xl"
              />
            </div>
          </form>

          {!query.trim() && (
            <div className="mt-8">
              <p className="label mb-4 text-faint">Popular searches</p>
              <ul className="flex flex-wrap gap-2">
                {SUGGESTIONS.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => setQuery(s)}
                      className="label border border-line-strong px-3.5 py-2 transition-colors hover:border-ink"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="mt-10">
            <p className="label mb-5 text-faint">
              {query.trim() ? `${results.length} result${results.length === 1 ? "" : "s"}` : "Best sellers"}
            </p>

            {query.trim() && results.length === 0 ? (
              <p className="text-sm text-muted">
                Nothing matched “{query}”. Try a colour, a fabric, or{" "}
                <Link href="/shop" className="link-underline text-ink" onClick={() => setSearchOpen(false)}>
                  browse everything
                </Link>
                .
              </p>
            ) : (
              <ul className="grid gap-x-6 gap-y-5 sm:grid-cols-2">
                {shown.map((product) => (
                  <li key={product.slug}>
                    <Link
                      href={`/shop/${product.slug}`}
                      onClick={() => setSearchOpen(false)}
                      className="group flex items-center gap-4"
                    >
                      <div className="relative aspect-square w-16 shrink-0 overflow-hidden bg-paper-deep">
                        <Image
                          src={product.colourways[0].images[0]}
                          alt=""
                          fill
                          sizes="64px"
                          className="object-cover transition-transform duration-[var(--duration-base)] group-hover:scale-105"
                        />
                      </div>
                      <div className="min-w-0">
                        <p className="truncate text-sm font-medium">{product.name}</p>
                        <p className="text-[0.8125rem] text-muted">{formatPrice(product.price)}</p>
                      </div>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </Overlay>
  );
}
