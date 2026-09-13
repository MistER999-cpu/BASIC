import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { lookbook } from "@/lib/editorial";

export const metadata: Metadata = {
  title: "Lookbook",
  description:
    "Seasonal campaigns shot flat against paper — the Rib Series, the knitting floor in Porto, and Winter Weights.",
  alternates: { canonical: "/lookbook" },
};

export default function LookbookPage() {
  return (
    <>
      <PageHeader
        eyebrow="Lookbook"
        title="Shot flat, against paper"
        lede="No styling beyond folding, no set beyond a sweep of paper. If the season is about the cloth, the photographs should be too."
        crumbs={[{ label: "Home", href: "/" }, { label: "Lookbook" }]}
      />

      <Container className="py-16 sm:py-20">
        <ul className="grid gap-x-8 gap-y-16 md:grid-cols-2">
          {lookbook.map((story, i) => (
            <Reveal
              as="li"
              key={story.slug}
              delay={(i % 2) * 90}
              className={i === 0 ? "md:col-span-2" : undefined}
            >
              <Link href={`/lookbook/${story.slug}`} className="group block">
                <div
                  className={`relative overflow-hidden bg-paper-deep ${
                    i === 0 ? "aspect-[2/1]" : "aspect-[4/5]"
                  }`}
                >
                  <Image
                    src={story.cover}
                    alt=""
                    fill
                    priority={i === 0}
                    sizes={i === 0 ? "100vw" : "(min-width: 768px) 50vw, 100vw"}
                    className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.03]"
                  />
                </div>
                <div className="mt-6 flex flex-col gap-3">
                  <span className="label text-muted">
                    {story.season} · {story.location} · {story.plates.length} plates
                  </span>
                  <h2 className="font-display text-title font-normal">
                    <span className="link-underline">{story.title}</span>
                  </h2>
                  <p className="max-w-xl text-lead text-ink-soft">{story.summary}</p>
                </div>
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </>
  );
}
