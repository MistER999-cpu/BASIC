import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { IconArrowRight } from "@/components/ui/icons";
import { helpDocs } from "@/lib/content";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Help",
  description: "Shipping, returns, sizing, garment care and the questions we are actually asked.",
  alternates: { canonical: "/help" },
};

export default function HelpPage() {
  return (
    <>
      <PageHeader
        eyebrow="Help"
        title="How can we help?"
        lede="Everything below is written plainly. If the answer is not here, the studio answers email within one working day."
        crumbs={[{ label: "Home", href: "/" }, { label: "Help" }]}
      />

      <Container className="py-16 sm:py-20">
        <ul className="grid gap-x-10 gap-y-10 sm:grid-cols-2 lg:grid-cols-3">
          {helpDocs.map((doc, i) => (
            <Reveal as="li" key={doc.slug} delay={(i % 3) * 70}>
              <Link
                href={`/help/${doc.slug}`}
                className="group flex h-full flex-col gap-3 border-t border-line pt-6"
              >
                <h2 className="font-display text-2xl leading-tight">
                  <span className="link-underline">{doc.title}</span>
                </h2>
                <p className="text-[0.9375rem] leading-relaxed text-muted">{doc.summary}</p>
                <IconArrowRight className="mt-2 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-1 group-hover:text-ink" />
              </Link>
            </Reveal>
          ))}
        </ul>

        <div className="mt-16 flex flex-col items-start gap-4 border-t border-line pt-10">
          <h2 className="font-display text-heading font-normal">Still stuck?</h2>
          <p className="max-w-xl text-lead text-ink-soft">
            Write to the studio and a person who has held the garment will reply — usually the
            same day.
          </p>
          <div className="flex flex-wrap items-center gap-6">
            <Link href="/contact" className="label link-underline">
              Contact the studio
            </Link>
            <a href={`mailto:${site.email}`} className="label link-underline text-muted hover:text-ink">
              {site.email}
            </a>
          </div>
        </div>
      </Container>
    </>
  );
}
