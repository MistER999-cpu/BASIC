import type { Metadata } from "next";
import Image from "next/image";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { Accordion } from "@/components/ui/Accordion";
import { EditorialSplit } from "@/components/sections/EditorialSplit";
import { materials } from "@/lib/content";

export const metadata: Metadata = {
  title: "Materials & responsibility",
  description:
    "Where our cloth is made, what it is made of, and the commitments we are prepared to publish figures against.",
  alternates: { canonical: "/sustainability" },
};

const FIGURES = [
  { value: "11", label: "styles in the line" },
  { value: "4", label: "mills, all named" },
  { value: "92%", label: "of the line in natural fibre" },
  { value: "0", label: "seasonal markdowns" },
];

export default function SustainabilityPage() {
  return (
    <>
      <PageHeader
        eyebrow="Materials & responsibility"
        title={<>Fewer things, made to last longer</>}
        lede="The most responsible garment is one you keep. Everything below is aimed at that — better fibre, named factories, and repairs for as long as we make the piece."
        crumbs={[{ label: "Home", href: "/" }, { label: "Materials" }]}
      />

      <section className="border-b border-line py-14">
        <Container>
          <dl className="grid grid-cols-2 gap-8 lg:grid-cols-4">
            {FIGURES.map((f, i) => (
              <Reveal key={f.label} delay={i * 60} className="flex flex-col gap-2">
                <dt className="font-display text-display leading-none">{f.value}</dt>
                <dd className="label text-muted">{f.label}</dd>
              </Reveal>
            ))}
          </dl>
        </Container>
      </section>

      <section className="border-b border-line py-20 sm:py-28">
        <Container>
          <h2 className="font-display text-title font-normal">The four materials</h2>
          <ul className="mt-12 grid gap-x-8 gap-y-12 sm:grid-cols-2">
            {materials.map((material, i) => (
              <Reveal as="li" key={material.name} delay={(i % 2) * 80} className="flex flex-col gap-5">
                <div className="relative aspect-[3/2] overflow-hidden bg-paper-deep">
                  <Image
                    src={material.image}
                    alt=""
                    fill
                    sizes="(min-width: 640px) 50vw, 100vw"
                    className="object-cover"
                  />
                </div>
                <div className="flex flex-col gap-2">
                  <span className="label text-muted">{material.origin}</span>
                  <h3 className="font-display text-2xl leading-tight">{material.name}</h3>
                  <p className="text-[0.9375rem] leading-relaxed text-ink-soft">{material.body}</p>
                </div>
              </Reveal>
            ))}
          </ul>
        </Container>
      </section>

      <EditorialSplit
        eyebrow="Repairs"
        title={<>Repaired, not replaced</>}
        body={[
          "Seams, hems and buttons are repaired free for as long as we are making the garment. Larger repairs are quoted at cost, with no margin on top.",
          "We would rather fix a piece four years old than sell a replacement. It is also the cheapest possible way to find out which of our seams are not good enough.",
        ]}
        image="/textures/rib-macro.jpg"
        imageAlt="Macro detail of rib knit structure"
        cta={{ href: "/contact", label: "Request a repair" }}
        tone="ink"
        aspect="landscape"
      />

      <section className="py-20 sm:py-28">
        <Container size="narrow">
          <h2 className="font-display text-title font-normal">Where we are not there yet</h2>
          <p className="mt-5 text-lead text-ink-soft">
            Publishing only the good numbers is marketing. These are the open problems.
          </p>
          <Accordion
            className="mt-10"
            items={[
              {
                title: "Shipping emissions",
                content: (
                  <p>
                    Everything moves by road and sea within Europe, but transatlantic orders fly.
                    We offset at twice the calculated tonnage, which is a mitigation, not a fix.
                    Consolidated weekly freight to a US hub is on the 2027 plan.
                  </p>
                ),
              },
              {
                title: "Elastane in the rib",
                content: (
                  <p>
                    Six percent elastane is what makes the neck recover, and it is also what makes
                    the garment hard to recycle. We have not found a bio-based alternative that
                    survives the wash tests. Until we do, we are choosing longevity over
                    recyclability and saying so plainly.
                  </p>
                ),
              },
              {
                title: "Returns",
                content: (
                  <p>
                    Free returns generate freight we would rather avoid. Our answer so far is a
                    size guide written to reduce them and a team that will tell you honestly what
                    to order. The return rate is 11%; the industry average is roughly 25%.
                  </p>
                ),
              },
              {
                title: "Certification",
                content: (
                  <p>
                    Our cotton is GOTS certified and the merino is mulesing-free and traceable to
                    the farm group. The leather consortium publishes water treatment figures. The
                    melton mill does not publish anything, and we are still pushing.
                  </p>
                ),
              },
            ]}
          />
        </Container>
      </section>
    </>
  );
}
