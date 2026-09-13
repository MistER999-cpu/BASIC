import { Img as Image } from "@/components/ui/Img";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Reveal } from "@/components/ui/Reveal";
import { lookbook } from "@/lib/editorial";

export function LookbookTeaser() {
  const stories = lookbook.slice(0, 3);

  return (
    <section className="border-b border-line py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Lookbook"
          title="Shot flat, against paper"
          lede="No styling beyond folding. The season is the rib, so we photographed the rib."
          link={{ href: "/lookbook", label: "All stories" }}
        />

        <ul className="mt-12 grid gap-x-6 gap-y-12 md:grid-cols-3">
          {stories.map((story, i) => (
            <Reveal as="li" key={story.slug} delay={i * 90}>
              <Link href={`/lookbook/${story.slug}`} className="group block">
                <div className="relative aspect-[3/4] overflow-hidden bg-paper-deep">
                  <Image
                    src={story.cover}
                    alt=""
                    fill
                    sizes="(min-width: 768px) 33vw, 100vw"
                    className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.04]"
                  />
                </div>
                <div className="mt-5 flex flex-col gap-2">
                  <span className="label text-muted">
                    {story.season} · {story.location}
                  </span>
                  <h3 className="font-display text-2xl leading-tight">
                    <span className="link-underline">{story.title}</span>
                  </h3>
                  <p className="text-sm leading-relaxed text-muted">{story.summary}</p>
                </div>
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
