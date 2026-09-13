import Image from "next/image";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Reveal } from "@/components/ui/Reveal";
import { journal } from "@/lib/editorial";
import { formatDate } from "@/lib/format";

export function JournalTeaser() {
  const [lead, ...rest] = journal.slice(0, 4);

  return (
    <section className="border-b border-line py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Journal"
          title="From the studio"
          link={{ href: "/journal", label: "Read the journal" }}
        />

        <div className="mt-12 grid gap-12 lg:grid-cols-2 lg:gap-16">
          <Reveal>
            <Link href={`/journal/${lead.slug}`} className="group block">
              <div className="relative aspect-[3/2] overflow-hidden bg-paper-deep">
                <Image
                  src={lead.cover}
                  alt=""
                  fill
                  sizes="(min-width: 1024px) 50vw, 100vw"
                  className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.03]"
                />
              </div>
              <div className="mt-5 flex flex-col gap-3">
                <span className="label text-muted">
                  {lead.category} · {lead.readingMinutes} min read
                </span>
                <h3 className="font-display text-3xl leading-tight">
                  <span className="link-underline">{lead.title}</span>
                </h3>
                <p className="max-w-lg text-lead text-ink-soft">{lead.excerpt}</p>
              </div>
            </Link>
          </Reveal>

          <ul className="flex flex-col">
            {rest.map((post, i) => (
              <Reveal as="li" key={post.slug} delay={i * 80} className="border-t border-line">
                <Link href={`/journal/${post.slug}`} className="group flex gap-6 py-6">
                  <div className="relative aspect-square w-24 shrink-0 overflow-hidden bg-paper-deep sm:w-32">
                    <Image
                      src={post.cover}
                      alt=""
                      fill
                      sizes="128px"
                      className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-105"
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    <span className="label text-muted">
                      {post.category} · {formatDate(post.publishedAt)}
                    </span>
                    <h3 className="font-display text-xl leading-snug">
                      <span className="link-underline">{post.title}</span>
                    </h3>
                    <p className="line-clamp-2 text-sm text-muted">{post.excerpt}</p>
                  </div>
                </Link>
              </Reveal>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  );
}
