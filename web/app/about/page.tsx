import type { Metadata } from "next";
import { Img as Image } from "@/components/ui/Img";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { EditorialSplit } from "@/components/sections/EditorialSplit";
import { ValueProps } from "@/components/sections/ValueProps";
import { NewsletterSection } from "@/components/sections/NewsletterSection";
import { Reveal } from "@/components/ui/Reveal";
import { ButtonLink } from "@/components/ui/Button";
import { timeline } from "@/lib/content";

export const metadata: Metadata = {
  title: "Our story",
  description:
    "BASIC makes eleven styles, restocked rather than replaced, in named mills in Portugal, Italy and England.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <>
      <PageHeader
        eyebrow="The studio"
        title={
          <>
            We started with one tank
            <br className="hidden sm:block" /> we could not stop reordering
          </>
        }
        lede="BASIC began in 2023 with two people, a sample run of forty pieces, and a conviction that a wardrobe does not need to be large to be complete."
        crumbs={[{ label: "Home", href: "/" }, { label: "About" }]}
      />

      <Container className="py-12 sm:py-16">
        <Reveal className="relative aspect-[21/9] w-full overflow-hidden bg-paper-deep">
          <Image
            src="/editorial/range.jpg"
            alt="The four colourways of the Ribbed Mock-Neck Tank laid out side by side"
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
        </Reveal>
      </Container>

      <EditorialSplit
        eyebrow="Why eleven"
        title={<>A line short enough to hold in your head</>}
        body={[
          "Most brands our size carry between eighty and two hundred styles. Every one of those is another fit to re-check each season, another mill relationship to maintain, another set of grading rules that can quietly go wrong between sample and production.",
          "At eleven, one person can hold all of it. We would rather re-cut the tank for a fourth time than release a twelfth style. The tank has been re-cut four times.",
        ]}
        image="/editorial/pair-warm.jpg"
        imageAlt="Sand and Clay tanks photographed together"
        cta={{ href: "/journal/why-we-only-make-eleven-things", label: "Read the full note" }}
      />

      <section className="border-b border-line py-20 sm:py-28">
        <Container>
          <div className="grid gap-12 lg:grid-cols-[minmax(0,20rem)_minmax(0,1fr)] lg:gap-20">
            <div>
              <h2 className="font-display text-title font-normal">How we got here</h2>
            </div>
            <ol className="flex flex-col">
              {timeline.map((entry, i) => (
                <Reveal
                  as="li"
                  key={entry.year}
                  delay={i * 70}
                  className="grid grid-cols-[4rem_minmax(0,1fr)] gap-6 border-t border-line py-6 sm:grid-cols-[6rem_minmax(0,1fr)] sm:gap-10"
                >
                  <span className="font-display text-2xl leading-none tabular-nums">{entry.year}</span>
                  <p className="text-lead text-ink-soft">{entry.text}</p>
                </Reveal>
              ))}
            </ol>
          </div>
        </Container>
      </section>

      <ValueProps />

      <EditorialSplit
        eyebrow="The people"
        title={<>Nineteen of us, one floor</>}
        body={[
          "The studio sits on the Distelweg in Amsterdam Noord — design, production and customer care in one room, which is the only reason a line this short stays this consistent.",
          "Every email is answered by someone who has held the garment. If something is wrong, the person replying has the authority to fix it without asking anyone.",
        ]}
        image="/textures/cloth-warm.jpg"
        imageAlt="Close detail of warm cotton jersey"
        cta={{ href: "/careers", label: "Open roles" }}
        tone="ink"
        flip
        aspect="landscape"
      />

      <section className="border-b border-line py-20 sm:py-24">
        <Container className="flex flex-col items-center gap-6 text-center">
          <h2 className="font-display text-title font-normal">Come and see it in person</h2>
          <p className="max-w-xl text-lead text-ink-soft">
            The Keizersgracht flagship carries the full line, and the showroom on the Distelweg
            opens by appointment.
          </p>
          <ButtonLink href="/stores" variant="outline" size="lg">
            Find a store
          </ButtonLink>
        </Container>
      </section>

      <NewsletterSection />
    </>
  );
}
