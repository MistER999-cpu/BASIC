import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { Hero } from "@/components/sections/Hero";
import { PressStrip } from "@/components/sections/PressStrip";
import { FeaturedRange } from "@/components/sections/FeaturedRange";
import { CategoryTiles } from "@/components/sections/CategoryTiles";
import { EditorialSplit } from "@/components/sections/EditorialSplit";
import { ValueProps } from "@/components/sections/ValueProps";
import { LookbookTeaser } from "@/components/sections/LookbookTeaser";
import { JournalTeaser } from "@/components/sections/JournalTeaser";
import { Testimonials } from "@/components/sections/Testimonials";
import { NewsletterSection } from "@/components/sections/NewsletterSection";
import { products } from "@/lib/products";
import { site } from "@/lib/site";
import { JsonLd } from "@/components/JsonLd";
import { organizationJsonLd, websiteJsonLd } from "@/lib/jsonld";

export const metadata: Metadata = {
  title: `${site.name} — ${site.tagline}`,
  description: site.description,
  alternates: { canonical: "/" },
};

export default function HomePage() {
  const newArrivals = [...products]
    .sort((a, b) => b.releasedAt.localeCompare(a.releasedAt))
    .slice(0, 4);

  return (
    <>
      <JsonLd data={[organizationJsonLd(), websiteJsonLd()]} />
      <Hero />
      <PressStrip />
      <FeaturedRange />

      <section className="border-b border-line py-20 sm:py-28">
        <Container>
          <SectionHeading
            eyebrow="Just landed"
            title="New arrivals"
            link={{ href: "/shop?sort=newest", label: "See everything new" }}
          />
          <ProductGrid products={newArrivals} className="mt-12" />
        </Container>
      </section>

      <CategoryTiles />

      <EditorialSplit
        eyebrow="The studio"
        title={<>Eleven things, made properly</>}
        body={[
          "Most brands our size carry between eighty and two hundred styles. We carry eleven, because that is the most we can hold a standard across.",
          "Every product page names the mill that made the cloth and the factory that sewed it. If we cannot name it, we do not sell it.",
        ]}
        image="/editorial/still-wide.jpg"
        imageAlt="Clay and Sand tanks laid flat side by side"
        cta={{ href: "/about", label: "Read our story" }}
        aspect="landscape"
      />

      <ValueProps />

      <EditorialSplit
        eyebrow="Materials"
        title={<>Long-staple cotton, extra-fine merino</>}
        body={[
          "Staple length is the single biggest predictor of whether a cotton garment will pill. Ours runs 34 mm and above — fewer joins in the yarn, a smoother surface, less friction.",
          "The merino is 18.5 micron, spun in Biella and traceable to the farm group. Fine enough to wear against the skin all day.",
        ]}
        image="/textures/rib-macro.jpg"
        imageAlt="Macro photograph of 2×1 rib knit at 220 gsm"
        cta={{ href: "/sustainability", label: "Materials & responsibility" }}
        tone="ink"
        flip
        aspect="landscape"
      />

      <LookbookTeaser />
      <Testimonials />
      <JournalTeaser />
      <NewsletterSection />
    </>
  );
}
