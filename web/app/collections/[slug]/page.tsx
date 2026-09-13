import type { Metadata } from "next";
import { Img as Image } from "@/components/ui/Img";
import { notFound } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { JsonLd } from "@/components/JsonLd";
import { collections, getCollection } from "@/lib/collections";
import { productsByCollection } from "@/lib/products";
import { breadcrumbJsonLd } from "@/lib/jsonld";

export function generateStaticParams() {
  return collections.map((c) => ({ slug: c.slug }));
}

export async function generateMetadata(props: PageProps<"/collections/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const collection = getCollection(slug);
  if (!collection) return { title: "Not found" };
  return {
    title: collection.name,
    description: collection.description,
    alternates: { canonical: `/collections/${collection.slug}` },
    openGraph: {
      title: collection.name,
      description: collection.tagline,
      images: [{ url: collection.image, alt: collection.name }],
    },
  };
}

export default async function CollectionPage(props: PageProps<"/collections/[slug]">) {
  const { slug } = await props.params;
  const collection = getCollection(slug);
  if (!collection) notFound();

  const items = productsByCollection(collection.slug);

  return (
    <>
      <JsonLd
        data={breadcrumbJsonLd([
          { name: "Home", url: "/" },
          { name: "Collections", url: "/collections" },
          { name: collection.name, url: `/collections/${collection.slug}` },
        ])}
      />

      <Container className="py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Collections", href: "/collections" },
            { label: collection.name },
          ]}
        />
      </Container>

      <section className="relative border-b border-line">
        <div className="relative aspect-[16/9] w-full overflow-hidden bg-paper-deep sm:aspect-[21/9]">
          <Image
            src={collection.image}
            alt={`${collection.name} — ${collection.tagline}`}
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
        </div>
        <Container className="py-12 sm:py-16">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-20">
            <div className="flex flex-col gap-5">
              <Eyebrow>{collection.season}</Eyebrow>
              <h1 className="font-display text-display font-normal">{collection.name}</h1>
              <p className="text-lead text-ink-soft">{collection.tagline}</p>
            </div>
            <p className="text-lead leading-relaxed text-ink-soft lg:pt-14">
              {collection.description}
            </p>
          </div>
        </Container>
      </section>

      <Container className="py-16 sm:py-20">
        <div className="mb-10 flex items-baseline justify-between border-b border-line pb-4">
          <h2 className="label">In this collection</h2>
          <p className="label text-muted">
            {items.length} {items.length === 1 ? "style" : "styles"}
          </p>
        </div>
        <ProductGrid products={items} priorityCount={2} />
      </Container>
    </>
  );
}
