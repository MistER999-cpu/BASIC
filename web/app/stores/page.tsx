import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { IconArrowRight } from "@/components/ui/icons";
import { stockistsByCountry } from "@/lib/stores";

export const metadata: Metadata = {
  title: "Stores & stockists",
  description:
    "The Amsterdam flagship, the Distelweg showroom, and the stores that carry BASIC across Europe, Japan and the United States.",
  alternates: { canonical: "/stores" },
};

export default function StoresPage() {
  const grouped = stockistsByCountry();

  return (
    <>
      <PageHeader
        eyebrow="Stores"
        title="Where to find us"
        lede="One flagship, one showroom by appointment, and a small number of stores whose buying we respect."
        crumbs={[{ label: "Home", href: "/" }, { label: "Stores" }]}
      />

      <Container className="py-16 sm:py-20">
        <div className="flex flex-col gap-16">
          {grouped.map(([country, stores], groupIndex) => (
            <section key={country} className="flex flex-col gap-8">
              <h2 className="label border-b border-line pb-4 text-muted">{country}</h2>
              <ul className="grid gap-x-10 gap-y-12 sm:grid-cols-2 lg:grid-cols-3">
                {stores.map((store, i) => (
                  <Reveal
                    as="li"
                    key={store.name}
                    delay={((groupIndex + i) % 3) * 70}
                    className="flex flex-col gap-3"
                  >
                    <span className="label text-clay">{store.type}</span>
                    <h3 className="font-display text-2xl leading-tight">{store.name}</h3>
                    <address className="text-[0.9375rem] leading-relaxed text-ink-soft not-italic">
                      {store.address.map((line) => (
                        <span key={line} className="block">
                          {line}
                        </span>
                      ))}
                    </address>
                    <ul className="flex flex-col gap-0.5 text-[0.8125rem] text-muted">
                      {store.hours.map((h) => (
                        <li key={h}>{h}</li>
                      ))}
                    </ul>
                    {store.phone && (
                      <a
                        href={`tel:${store.phone.replace(/\s/g, "")}`}
                        className="link-underline self-start text-[0.8125rem] text-muted hover:text-ink"
                      >
                        {store.phone}
                      </a>
                    )}
                    <a
                      href={store.mapUrl}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="label group mt-1 inline-flex items-center gap-2 self-start"
                    >
                      Directions
                      <IconArrowRight className="transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-1" />
                    </a>
                  </Reveal>
                ))}
              </ul>
            </section>
          ))}
        </div>
      </Container>
    </>
  );
}
