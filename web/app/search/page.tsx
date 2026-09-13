import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { SearchField } from "@/components/commerce/SearchField";
import { searchProducts } from "@/lib/products";

export const metadata: Metadata = {
  title: "Search",
  description: "Search the BASIC line by style, colour or fabric.",
  robots: { index: false, follow: true },
};

export default async function SearchPage(props: PageProps<"/search">) {
  const params = await props.searchParams;
  const raw = Array.isArray(params.q) ? params.q[0] : params.q;
  const query = (raw ?? "").trim();
  const results = query ? searchProducts(query) : [];

  return (
    <>
      <PageHeader
        eyebrow="Search"
        title={query ? `“${query}”` : "Search"}
        lede={
          query
            ? `${results.length} ${results.length === 1 ? "style matches" : "styles match"} your search.`
            : "Search the line by style, colour or fabric."
        }
        crumbs={[{ label: "Home", href: "/" }, { label: "Search" }]}
      >
        <SearchField initialQuery={query} className="mt-4 max-w-xl" />
      </PageHeader>

      <Container className="py-16 sm:py-20">
        {query && results.length === 0 ? (
          <div className="flex flex-col items-start gap-5">
            <p className="font-display text-2xl">Nothing matched “{query}”</p>
            <p className="max-w-lg text-lead text-ink-soft">
              The line is eleven styles, so a narrow search often comes back empty. Try a colour
              like “clay”, a fabric like “merino”, or browse everything.
            </p>
            <Link href="/shop" className="label link-underline">
              Shop everything
            </Link>
          </div>
        ) : query ? (
          <ProductGrid products={results} columns={4} priorityCount={4} />
        ) : null}
      </Container>
    </>
  );
}
