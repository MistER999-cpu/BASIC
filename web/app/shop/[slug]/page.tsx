import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { ProductDetail } from "@/components/commerce/ProductDetail";
import { ProductGrid } from "@/components/commerce/ProductGrid";
import { JsonLd } from "@/components/JsonLd";
import { getProduct, products, relatedProducts, getCategory } from "@/lib/products";
import { breadcrumbJsonLd, productJsonLd } from "@/lib/jsonld";

export function generateStaticParams() {
  return products.map((product) => ({ slug: product.slug }));
}

export async function generateMetadata(props: PageProps<"/shop/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const product = getProduct(slug);
  if (!product) return { title: "Not found" };

  return {
    title: product.name,
    description: product.tagline,
    alternates: { canonical: `/shop/${product.slug}` },
    openGraph: {
      type: "website",
      title: product.name,
      description: product.tagline,
      url: `/shop/${product.slug}`,
      images: [{ url: product.colourways[0].images[0], width: 1200, height: 1600, alt: product.name }],
    },
  };
}

export default async function ProductPage(props: PageProps<"/shop/[slug]">) {
  const { slug } = await props.params;
  const product = getProduct(slug);
  if (!product) notFound();

  const category = getCategory(product.category);
  const related = relatedProducts(product, 4);

  const crumbs = [
    { label: "Home", href: "/" },
    { label: "Shop", href: "/shop" },
    ...(category ? [{ label: category.name, href: `/shop?category=${category.slug}` }] : []),
    { label: product.name },
  ];

  return (
    <>
      <JsonLd
        data={[
          productJsonLd(product),
          breadcrumbJsonLd([
            { name: "Home", url: "/" },
            { name: "Shop", url: "/shop" },
            { name: product.name, url: `/shop/${product.slug}` },
          ]),
        ]}
      />

      <Container className="py-6 sm:py-8">
        <Breadcrumbs items={crumbs} />
      </Container>

      <Container className="pb-20 sm:pb-28">
        <Suspense fallback={<div className="min-h-[60vh]" />}>
          <ProductDetail product={product} />
        </Suspense>
      </Container>

      <section className="border-t border-line py-20 sm:py-24">
        <Container>
          <SectionHeading
            eyebrow="Complete the look"
            title="Wears well with"
            link={{ href: "/shop", label: "Shop everything" }}
          />
          <ProductGrid products={related} className="mt-12" />
        </Container>
      </section>
    </>
  );
}
