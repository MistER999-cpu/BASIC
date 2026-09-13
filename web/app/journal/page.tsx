import type { Metadata } from "next";
import { Img as Image } from "@/components/ui/Img";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { journal } from "@/lib/editorial";
import { formatDate } from "@/lib/format";

export const metadata: Metadata = {
  title: "Journal",
  description:
    "Notes from the studio on materials, craft, care, and why we only make eleven things.",
  alternates: { canonical: "/journal" },
};

export default function JournalPage() {
  const categories = [...new Set(journal.map((p) => p.category))];

  return (
    <>
      <PageHeader
        eyebrow="Journal"
        title="From the studio"
        lede="What we made, what we got wrong, and the parts of the process that usually stay behind the label."
        crumbs={[{ label: "Home", href: "/" }, { label: "Journal" }]}
      />

      <Container className="py-12 sm:py-16">
        <ul className="flex flex-wrap gap-2 border-b border-line pb-8">
          {categories.map((category) => (
            <li key={category}>
              <span className="label border border-line-strong px-3.5 py-2 text-ink-soft">
                {category}
              </span>
            </li>
          ))}
        </ul>

        <ul className="mt-12 grid gap-x-8 gap-y-14 md:grid-cols-2 lg:grid-cols-3">
          {journal.map((post, i) => (
            <Reveal
              as="li"
              key={post.slug}
              delay={(i % 3) * 80}
              className={i === 0 ? "md:col-span-2 lg:col-span-3" : undefined}
            >
              <Link
                href={`/journal/${post.slug}`}
                className={`group ${i === 0 ? "grid gap-8 md:grid-cols-2 md:items-center md:gap-14" : "block"}`}
              >
                <div
                  className={`relative overflow-hidden bg-paper-deep ${
                    i === 0 ? "aspect-[3/2]" : "aspect-[4/3]"
                  }`}
                >
                  <Image
                    src={post.cover}
                    alt=""
                    fill
                    priority={i === 0}
                    sizes={i === 0 ? "(min-width: 768px) 50vw, 100vw" : "(min-width: 1024px) 33vw, 50vw"}
                    className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-[1.04]"
                  />
                </div>
                <div className="mt-5 flex flex-col gap-3 md:mt-0">
                  <span className="label text-muted">
                    {post.category} · {formatDate(post.publishedAt)} · {post.readingMinutes} min
                  </span>
                  <h2
                    className={`font-display leading-tight ${i === 0 ? "text-title" : "text-2xl"}`}
                  >
                    <span className="link-underline">{post.title}</span>
                  </h2>
                  <p className={i === 0 ? "max-w-lg text-lead text-ink-soft" : "text-sm text-muted"}>
                    {post.excerpt}
                  </p>
                </div>
              </Link>
            </Reveal>
          ))}
        </ul>
      </Container>
    </>
  );
}
