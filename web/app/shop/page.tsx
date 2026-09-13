import type { Metadata } from "next";
import { Suspense } from "react";
import { ShopBrowser } from "@/components/commerce/ShopBrowser";
import { PageHeader } from "@/components/layout/PageHeader";

export const metadata: Metadata = {
  title: "Ready-to-wear",
  description:
    "Eleven styles in long-staple cotton, extra-fine merino and Yorkshire melton. Filter by category, colour and price.",
  alternates: { canonical: "/shop" },
};

export default function ShopPage() {
  return (
    <Suspense
      fallback={
        <PageHeader
          eyebrow="Ready-to-wear"
          title="Everything"
          lede="Eleven styles, restocked rather than replaced."
          crumbs={[{ label: "Home", href: "/" }, { label: "Shop" }]}
        />
      }
    >
      <ShopBrowser />
    </Suspense>
  );
}
