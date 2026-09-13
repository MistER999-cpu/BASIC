import Image from "next/image";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Reveal } from "@/components/ui/Reveal";
import { categories } from "@/lib/products";
import { IconArrowRight } from "@/components/ui/icons";

export function CategoryTiles() {
  return (
    <section className="border-b border-line py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Browse"
          title="By category"
          link={{ href: "/shop", label: "All ready-to-wear" }}
        />

        <ul className="mt-12 grid grid-cols-2 gap-x-4 gap-y-10 sm:gap-x-6 lg:grid-cols-3">
          {categories.map((category, i) => (
            <Reveal as="li" key={category.slug} delay={(i % 3) * 80}>
              <Link href={`/shop?category=${category.slug}`} className="group block">
                <div className="relative aspect-[4/5] overflow-hidden bg-paper-deep">
                  <Image
                    src={category.image}
                    alt=""
                    fill
                    sizes="(min-width: 1024px) 33vw, 50vw"
                    className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.04]"
                  />
                </div>
                <div className="mt-4 flex items-start justify-between gap-4">
                  <div>
                    <h3 className="font-display text-xl leading-tight">{category.name}</h3>
                    <p className="mt-1 text-[0.8125rem] text-muted">{category.blurb}</p>
                  </div>
                  <IconArrowRight className="mt-1.5 shrink-0 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-1 group-hover:text-ink" />
                </div>
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
