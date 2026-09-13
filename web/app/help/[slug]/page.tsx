import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { JsonLd } from "@/components/JsonLd";
import { helpDocs, getHelpDoc, sizeChart } from "@/lib/content";
import { faqJsonLd } from "@/lib/jsonld";
import { formatDate } from "@/lib/format";

export function generateStaticParams() {
  return helpDocs.map((d) => ({ slug: d.slug }));
}

export async function generateMetadata(props: PageProps<"/help/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const doc = getHelpDoc(slug);
  if (!doc) return { title: "Not found" };
  return {
    title: doc.title,
    description: doc.summary,
    alternates: { canonical: `/help/${doc.slug}` },
  };
}

export default async function HelpDocPage(props: PageProps<"/help/[slug]">) {
  const { slug } = await props.params;
  const doc = getHelpDoc(slug);
  if (!doc) notFound();

  const faq =
    doc.slug === "faq"
      ? doc.sections
          .filter((s) => s.heading && s.paragraphs)
          .map((s) => ({ question: s.heading!, answer: s.paragraphs!.join(" ") }))
      : null;

  return (
    <>
      {faq && <JsonLd data={faqJsonLd(faq)} />}

      <Container className="py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Help", href: "/help" },
            { label: doc.title },
          ]}
        />
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

          {doc.slug === "size-guide" && (
            <section className="flex flex-col gap-4">
              <h2 className="font-display text-heading font-normal">Body measurements</h2>
              <p className="text-[0.9375rem] text-muted">All measurements in centimetres.</p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[36rem] border-collapse text-left">
                  <caption className="sr-only">
                    Body measurements by size, in centimetres
                  </caption>
                  <thead>
                    <tr className="border-b border-ink">
                      {sizeChart.columns.map((col) => (
                        <th key={col} scope="col" className="label py-3 pr-4 font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {sizeChart.rows.map((row) => (
                      <tr key={row[0]} className="border-b border-line">
                        <th scope="row" className="label py-4 pr-4 font-medium">
                          {row[0]}
                        </th>
                        {row.slice(1).map((cell, i) => (
                          <td key={i} className="py-4 pr-4 text-[0.9375rem] tabular-nums text-ink-soft">
                            {cell}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}
        </div>

        <nav aria-label="Other help topics" className="mt-16 border-t border-line pt-8">
          <h2 className="label mb-5 text-faint">Other topics</h2>
          <ul className="flex flex-wrap gap-x-6 gap-y-3">
            {helpDocs
              .filter((d) => d.slug !== doc.slug)
              .map((d) => (
                <li key={d.slug}>
                  <Link href={`/help/${d.slug}`} className="label link-underline text-muted hover:text-ink">
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
