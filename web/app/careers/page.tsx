import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { Reveal } from "@/components/ui/Reveal";
import { IconArrowRight } from "@/components/ui/icons";
import { roles } from "@/lib/content";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Careers",
  description: "Open roles at the BASIC studio in Amsterdam Noord.",
  alternates: { canonical: "/careers" },
};

const PRINCIPLES = [
  {
    title: "One floor",
    body: "Design, production and customer care share a room. Nobody hands a problem to another department.",
  },
  {
    title: "No commission",
    body: "Retail is paid a salary, not a percentage. There are no targets and nothing to upsell.",
  },
  {
    title: "Four weeks, properly off",
    body: "Twenty-five days plus the week between Christmas and New Year, when the studio closes entirely.",
  },
  {
    title: "You go to the factory",
    body: "Everyone in production and design spends at least one week a season on a factory floor.",
  },
];

export default function CareersPage() {
  return (
    <>
      <PageHeader
        eyebrow="Careers"
        title="Work with us"
        lede="Nineteen people on one floor in Amsterdam Noord. We hire slowly and we keep people a long time."
        crumbs={[{ label: "Home", href: "/" }, { label: "Careers" }]}
      />

      <section className="border-b border-line py-16 sm:py-20">
        <Container>
          <h2 className="label mb-10 text-muted">Open roles</h2>
          <ul className="flex flex-col">
            {roles.map((role, i) => (
              <Reveal as="li" key={role.slug} delay={i * 60} className="border-t border-line">
                <a
                  href={`mailto:${site.email}?subject=${encodeURIComponent(`Application — ${role.title}`)}`}
                  className="group grid items-start gap-4 py-8 md:grid-cols-[minmax(0,1fr)_12rem_auto] md:items-center md:gap-10"
                >
                  <div className="flex flex-col gap-2">
                    <h3 className="font-display text-2xl leading-tight">
                      <span className="link-underline">{role.title}</span>
                    </h3>
                    <p className="max-w-xl text-[0.9375rem] leading-relaxed text-muted">
                      {role.summary}
                    </p>
                  </div>
                  <div className="flex flex-col gap-1">
                    <span className="label text-ink-soft">{role.location}</span>
                    <span className="label text-faint">
                      {role.team} · {role.type}
                    </span>
                  </div>
                  <IconArrowRight className="hidden shrink-0 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-2 group-hover:text-ink md:block" />
                </a>
              </Reveal>
            ))}
          </ul>
          <p className="mt-10 text-[0.9375rem] text-muted">
            Nothing that fits? Write to{" "}
            <a href={`mailto:${site.email}`} className="link-underline text-ink">
              {site.email}
            </a>{" "}
            anyway — we read everything and keep good letters on file.
          </p>
        </Container>
      </section>

      <section className="py-20 sm:py-24">
        <Container>
          <h2 className="font-display text-title font-normal">How we work</h2>
          <ul className="mt-12 grid gap-10 sm:grid-cols-2 lg:grid-cols-4">
            {PRINCIPLES.map((p, i) => (
              <Reveal as="li" key={p.title} delay={i * 70} className="flex flex-col gap-3">
                <span aria-hidden className="label text-faint tabular-nums">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <h3 className="font-display text-xl leading-tight">{p.title}</h3>
                <p className="text-sm leading-relaxed text-muted">{p.body}</p>
              </Reveal>
            ))}
          </ul>
        </Container>
      </section>
    </>
  );
}
