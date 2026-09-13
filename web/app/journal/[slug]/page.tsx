import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { JsonLd } from "@/components/JsonLd";
import { IconArrowRight } from "@/components/ui/icons";
import { journal, getJournalPost } from "@/lib/editorial";
import { formatDate } from "@/lib/format";
import { articleJsonLd } from "@/lib/jsonld";

export function generateStaticParams() {
  return journal.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata(props: PageProps<"/journal/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const post = getJournalPost(slug);
  if (!post) return { title: "Not found" };
  return {
    title: post.title,
    description: post.excerpt,
    alternates: { canonical: `/journal/${post.slug}` },
    openGraph: {
      type: "article",
      title: post.title,
      description: post.excerpt,
      publishedTime: post.publishedAt,
      images: [{ url: post.cover, alt: post.title }],
    },
  };
}

export default async function JournalPostPage(props: PageProps<"/journal/[slug]">) {
  const { slug } = await props.params;
  const post = getJournalPost(slug);
  if (!post) notFound();

  const index = journal.findIndex((p) => p.slug === post.slug);
  const next = journal[(index + 1) % journal.length];

  return (
    <>
      <JsonLd data={articleJsonLd(post)} />

      <Container className="py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Journal", href: "/journal" },
            { label: post.title },
          ]}
        />
      </Container>

      <Container size="narrow" className="pb-10">
        <header className="flex flex-col gap-5 text-center">
          <p className="label text-muted">
            {post.category} · {formatDate(post.publishedAt)} · {post.readingMinutes} min read
          </p>
          <h1 className="font-display text-display font-normal">{post.title}</h1>
          <p className="text-lead text-ink-soft">{post.excerpt}</p>
          <p className="label text-faint">Words — {post.author}</p>
        </header>
      </Container>

      <Container className="pb-12 sm:pb-16">
        <div className="relative aspect-[2/1] w-full overflow-hidden bg-paper-deep">
          <Image
            src={post.cover}
            alt=""
            fill
            priority
            sizes="100vw"
            className="object-cover"
          />
        </div>
      </Container>

      <Container size="narrow" className="pb-20 sm:pb-28">
        <article className="flex flex-col gap-10">
          {post.body.map((section, i) => (
            <section key={i} className="flex flex-col gap-4">
              {section.heading && (
                <h2 className="font-display text-heading font-normal">{section.heading}</h2>
              )}
              {section.paragraphs.map((paragraph) => (
                <p key={paragraph} className="text-lead leading-relaxed text-ink-soft">
                  {paragraph}
                </p>
              ))}
            </section>
          ))}
        </article>
      </Container>

      <section className="border-t border-line">
        <Container>
          <Link
            href={`/journal/${next.slug}`}
            className="group flex items-center justify-between gap-8 py-12"
          >
            <div className="flex flex-col gap-2">
              <span className="label text-muted">Next in the journal</span>
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
