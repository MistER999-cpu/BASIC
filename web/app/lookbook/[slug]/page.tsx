import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Reveal } from "@/components/ui/Reveal";
import { IconArrowRight } from "@/components/ui/icons";
import { lookbook, getLookbookStory } from "@/lib/editorial";
import { cn } from "@/lib/cn";

export function generateStaticParams() {
  return lookbook.map((s) => ({ slug: s.slug }));
}

export async function generateMetadata(props: PageProps<"/lookbook/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const story = getLookbookStory(slug);
  if (!story) return { title: "Not found" };
  return {
    title: story.title,
    description: story.summary,
    alternates: { canonical: `/lookbook/${story.slug}` },
    openGraph: {
      title: story.title,
      description: story.summary,
      images: [{ url: story.cover, alt: story.title }],
    },
  };
}

export default async function LookbookStoryPage(props: PageProps<"/lookbook/[slug]">) {
  const { slug } = await props.params;
  const story = getLookbookStory(slug);
  if (!story) notFound();

  const index = lookbook.findIndex((s) => s.slug === story.slug);
  const next = lookbook[(index + 1) % lookbook.length];

  return (
    <>
      <Container className="py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Lookbook", href: "/lookbook" },
            { label: story.title },
          ]}
        />
      </Container>

      <Container className="pb-12">
        <div className="grid gap-8 border-b border-line pb-12 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:gap-20">
          <div className="flex flex-col gap-5">
            <Eyebrow>
              {story.season} — {story.location}
            </Eyebrow>
            <h1 className="font-display text-display font-normal">{story.title}</h1>
          </div>
          <div className="flex flex-col gap-4 lg:pt-12">
            <p className="text-lead text-ink-soft">{story.summary}</p>
            <p className="label text-muted">{story.credit}</p>
          </div>
        </div>
      </Container>

      <Container className="pb-20 sm:pb-28">
        <ul className="grid gap-x-6 gap-y-6 md:grid-cols-2">
          {story.plates.map((plate, i) => (
            <Reveal
              as="li"
              key={plate.src + i}
              delay={(i % 2) * 80}
              className={cn(plate.wide && "md:col-span-2")}
            >
              <figure>
                <div
                  className={cn(
                    "relative overflow-hidden bg-paper-deep",
                    plate.wide ? "aspect-[2/1]" : "aspect-[4/5]",
                  )}
                >
                  <Image
                    src={plate.src}
                    alt={plate.caption}
                    fill
                    priority={i === 0}
                    sizes={plate.wide ? "100vw" : "(min-width: 768px) 50vw, 100vw"}
                    className="object-cover"
                  />
                </div>
                <figcaption className="label mt-3 text-muted">{plate.caption}</figcaption>
              </figure>
            </Reveal>
          ))}
        </ul>
      </Container>

      <section className="border-t border-line">
        <Container>
          <Link href={`/lookbook/${next.slug}`} className="group flex items-center justify-between gap-8 py-12">
            <div className="flex flex-col gap-2">
              <span className="label text-muted">Next story</span>
              <span className="font-display text-title">
                <span className="link-underline">{next.title}</span>
              </span>
            </div>
            <IconArrowRight className="shrink-0 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-2 group-hover:text-ink" />
          </Link>
        </Container>
      </section>
    </>
  );
}
