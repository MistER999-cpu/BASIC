import type { Metadata } from "next";
import { Suspense } from "react";
import { PageHeader } from "@/components/layout/PageHeader";
import { SearchResults } from "@/components/commerce/SearchResults";

export const metadata: Metadata = {
  title: "Search",
  description: "Search the BASIC line by style, colour or fabric.",
  robots: { index: false, follow: true },
};

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <PageHeader
          eyebrow="Search"
          title="Search"
          lede="Search the line by style, colour or fabric."
          crumbs={[{ label: "Home", href: "/" }, { label: "Search" }]}
        />
      }
    >
      <SearchResults />
    </Suspense>
  );
}
