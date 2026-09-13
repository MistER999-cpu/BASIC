import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { legalDocs, getLegalDoc } from "@/lib/content";
import { formatDate } from "@/lib/format";

export function generateStaticParams() {
  return legalDocs.map((d) => ({ slug: d.slug }));
}

export async function generateMetadata(props: PageProps<"/legal/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const doc = getLegalDoc(slug);
  if (!doc) return { title: "Not found" };
  return {
    title: doc.title,
    description: doc.summary,
    alternates: { canonical: `/legal/${doc.slug}` },
  };
}

export default async function LegalDocPage(props: PageProps<"/legal/[slug]">) {
  const { slug } = await props.params;
  const doc = getLegalDoc(slug);
  if (!doc) notFound();

  return (
    <>
      <Container className="py-6 sm:py-8">
        <Breadcrumbs items={[{ label: "Home", href: "/" }, { label: doc.title }]} />
      </Container>

      <Container size="narrow" className="pb-20 sm:pb-28">
        <header className="flex flex-col gap-4 border-b border-line pb-10">
          <h1 className="font-display text-display font-normal">{doc.title}</h1>
          <p className="text-lead text-ink-soft">{doc.summary}</p>
          <p className="label text-faint">Last updated {formatDate(doc.updatedAt)}</p>
        </header>

        <div className="flex flex-col gap-10 pt-10">
          {doc.sections.map((section, i) => (
            <section key={i} className="flex flex-col gap-4">
              {section.heading && (
                <h2 className="font-display text-heading font-normal">{section.heading}</h2>
              )}
              {section.paragraphs?.map((p) => (
                <p key={p} className="text-lead leading-relaxed text-ink-soft">
                  {p}
                </p>
              ))}
              {section.list && (
                <ul className="flex flex-col gap-2.5">
                  {section.list.map((item) => (
                    <li
                      key={item}
                      className="grid grid-cols-[1rem_minmax(0,1fr)] gap-2 text-[0.9375rem] leading-relaxed text-ink-soft"
                    >
                      <span aria-hidden className="text-faint">
                        —
                      </span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              )}
            </section>
          ))}
        </div>

        <nav aria-label="Other legal pages" className="mt-16 border-t border-line pt-8">
          <ul className="flex flex-wrap gap-x-6 gap-y-3">
            {legalDocs
              .filter((d) => d.slug !== doc.slug)
              .map((d) => (
                <li key={d.slug}>
                  <Link href={`/legal/${d.slug}`} className="label link-underline text-muted hover:text-ink">
                    {d.title}
                  </Link>
                </li>
              ))}
          </ul>
        </nav>
      </Container>
    </>
  );
}
