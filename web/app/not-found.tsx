import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/Eyebrow";

const ELSEWHERE = [
  { label: "Ready-to-wear", href: "/shop" },
  { label: "The Rib Series", href: "/collections/rib-series" },
  { label: "Lookbook", href: "/lookbook" },
  { label: "Journal", href: "/journal" },
  { label: "Help", href: "/help" },
];

export default function NotFound() {
  return (
    <Container className="flex min-h-[70vh] flex-col justify-center py-24">
      <div className="flex max-w-2xl flex-col gap-7">
        <Eyebrow>Error 404</Eyebrow>
        <h1 className="font-display text-hero font-normal">
          Not <span className="italic">here</span>
        </h1>
        <p className="text-lead text-ink-soft">
          The page you were after has moved or never existed. The line is only eleven styles, so
          it will not take long to find what you wanted.
        </p>
        <div className="flex flex-wrap items-center gap-4">
          <ButtonLink href="/shop" size="lg">
            Shop everything
          </ButtonLink>
          <ButtonLink href="/" variant="ghost" size="lg">
            Back home
          </ButtonLink>
        </div>
        <nav aria-label="Elsewhere on the site" className="mt-6 border-t border-line pt-6">
          <ul className="flex flex-wrap gap-x-6 gap-y-3">
            {ELSEWHERE.map((link) => (
              <li key={link.href}>
                <Link href={link.href} className="label link-underline text-muted hover:text-ink">
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
      </div>
    </Container>
  );
}
