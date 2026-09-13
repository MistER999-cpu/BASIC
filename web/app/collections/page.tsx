import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { IconArrowRight } from "@/components/ui/icons";
import { collections } from "@/lib/collections";
import { productsByCollection } from "@/lib/products";

export const metadata: Metadata = {
  title: "Collections",
  description:
    "Seasonal and permanent collections — the Rib Series, Core Essentials, Winter Weights, the Neutrals and the Layering Edit.",
  alternates: { canonical: "/collections" },
};

export default function CollectionsPage() {
  return (
    <>
      <PageHeader
        eyebrow="Collections"
        title="Five ways in"
        lede="Two seasonal collections and three that stay in the line year-round. Nothing here is discontinued without notice."
        crumbs={[{ label: "Home", href: "/" }, { label: "Collections" }]}
      />

      <Container className="py-16 sm:py-20">
        <ul className="flex flex-col">
          {collections.map((collection, i) => {
            const count = productsByCollection(collection.slug).length;
            return (
              <Reveal as="li" key={collection.slug} delay={i * 60} className="border-b border-line">
                <Link
                  href={`/collections/${collection.slug}`}
                  className="group grid items-center gap-8 py-10 md:grid-cols-[18rem_minmax(0,1fr)_auto] md:gap-12"
                >
                  <div className="relative aspect-[4/3] overflow-hidden bg-paper-deep md:aspect-[4/3]">
                    <Image
                      src={collection.image}
                      alt=""
                      fill
                      sizes="(min-width: 768px) 288px, 100vw"
                      className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.05]"
                    />
                  </div>

                  <div className="flex flex-col gap-3">
                    <span className="label text-muted">
                      {collection.season} · {count} {count === 1 ? "style" : "styles"}
                    </span>
                    <h2 className="font-display text-title font-normal">
                      <span className="link-underline">{collection.name}</span>
                    </h2>
                    <p className="max-w-xl text-lead text-ink-soft">{collection.tagline}</p>
                  </div>

                  <IconArrowRight className="hidden shrink-0 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-2 group-hover:text-ink md:block" />
                </Link>
              </Reveal>
            );
          })}
        </ul>
      </Container>
    </>
  );
}
