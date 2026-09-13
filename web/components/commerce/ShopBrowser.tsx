"use client";

import { useSearchParams } from "next/navigation";
import { useMemo } from "react";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { FilterRail, FilterToolbar } from "@/components/commerce/FilterBar";
import { ButtonLink } from "@/components/ui/Button";
import { getCategory } from "@/lib/products";
import { queryProducts } from "@/lib/shop-query";

/**
 * Reads the filter state from the URL on the client, so the page itself is a
 * static document that any host can serve while the grid stays filterable and
 * every filtered view remains a shareable link.
 */
export function ShopBrowser() {
  const params = useSearchParams();

  const query = useMemo(
    () => ({
      category: params.get("category") ?? undefined,
      colour: params.get("colour") ?? undefined,
      price: params.get("price") ?? undefined,
      sort: params.get("sort") ?? undefined,
      tag: params.get("tag") ?? undefined,
    }),
    [params],
  );

  const results = useMemo(() => queryProducts(query), [query]);
  const category = query.category ? getCategory(query.category) : undefined;

  return (
    <>
      <PageHeader
        eyebrow="Ready-to-wear"
        title={category ? category.name : "Everything"}
        lede={
          category
            ? category.blurb
            : "Eleven styles, restocked rather than replaced. Every page names the mill that made the cloth and the factory that sewed it."
        }
        crumbs={[
          { label: "Home", href: "/" },
          { label: "Shop", href: category ? "/shop" : undefined },
          ...(category ? [{ label: category.name }] : []),
        ]}
      />

      <Container className="py-10 sm:py-14">
        <div className="grid gap-10 lg:grid-cols-[12rem_minmax(0,1fr)] lg:gap-16">
          <aside className="hidden lg:sticky lg:top-28 lg:block lg:self-start">
            <h2 className="sr-only">Filters</h2>
            <FilterRail />
          </aside>

          <div>
            <FilterToolbar total={results.length} />

            {results.length === 0 ? (
              <div className="flex flex-col items-start gap-6 py-20">
                <p className="font-display text-2xl">Nothing matches those filters</p>
                <p className="max-w-md text-muted">
                  Try a wider price band or a different colour — the line is short by design.
                </p>
                <ButtonLink href="/shop" variant="outline">
                  Clear filters
                </ButtonLink>
              </div>
            ) : (
              <ProductGrid products={results} columns={3} priorityCount={3} className="mt-10" />
            )}
          </div>
        </div>
      </Container>
    </>
  );
}
