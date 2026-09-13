import Link from "next/link";
import { footerNav, legalNav, site } from "@/lib/site";
import { Container } from "@/components/ui/Container";
import { NewsletterForm } from "@/components/ui/NewsletterForm";
import { Marquee } from "@/components/ui/Marquee";

const PAYMENTS = ["Visa", "Mastercard", "Amex", "iDEAL", "PayPal", "Apple Pay", "Klarna"];

export function Footer() {
  return (
    <footer className="mt-auto bg-ink text-paper">
      <Marquee
        className="border-b border-paper/12 py-4 text-paper/70"
        items={[
          "Free delivery over €150",
          "30-day returns",
          "Repaired, not replaced",
          "Made in Portugal, Italy & England",
          "Duties prepaid to the EU, UK, US & Canada",
        ]}
      />

      <Container className="py-16 sm:py-20">
        <div className="grid gap-14 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-6">
            <p className="font-display text-3xl leading-tight">{site.tagline}</p>
            <p className="max-w-sm text-sm leading-relaxed text-paper/65">
              One letter a month: what we made, what we got wrong, and what is coming back in stock.
              No offers, because we do not run them.
            </p>
            <NewsletterForm tone="light" className="max-w-sm" />
          </div>

          <nav aria-label="Footer" className="grid grid-cols-2 gap-10 sm:grid-cols-4">
            {footerNav.map((group) => (
              <div key={group.heading} className="flex flex-col gap-4">
                <h2 className="label text-paper/60">{group.heading}</h2>
                <ul className="flex flex-col gap-2.5">
                  {group.links.map((link) => (
                    <li key={link.href + link.label}>
                      <Link
                        href={link.href}
                        className="link-underline text-sm text-paper/80 hover:text-paper"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </nav>
        </div>

        <div className="mt-16 grid gap-10 border-t border-paper/12 pt-10 lg:grid-cols-[minmax(0,22rem)_1fr] lg:gap-20">
          <div className="flex flex-col gap-3">
            <h2 className="label text-paper/60">Studio</h2>
            <address className="text-sm leading-relaxed text-paper/70 not-italic">
              {site.address.street}
              <br />
              {site.address.postalCode} {site.address.city}
              <br />
              {site.address.country}
            </address>
            <a href={`mailto:${site.email}`} className="link-underline self-start text-sm text-paper/80">
              {site.email}
            </a>
          </div>

          <div className="flex flex-col gap-8">
            <div className="flex flex-col gap-3">
              <h2 className="label text-paper/60">Follow</h2>
              <ul className="flex flex-wrap gap-x-6 gap-y-2">
                {site.socials.map((s) => (
                  <li key={s.label}>
                    <a
                      href={s.href}
                      target="_blank"
                      rel="noreferrer noopener"
                      className="link-underline text-sm text-paper/80 hover:text-paper"
                    >
                      {s.label}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div className="flex flex-col gap-3">
              <h2 className="label text-paper/60">Payment</h2>
              <ul className="flex flex-wrap gap-2">
                {PAYMENTS.map((p) => (
                  <li
                    key={p}
                    className="label border border-paper/20 px-2.5 py-1.5 text-paper/60"
                  >
                    {p}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="mt-14 flex flex-col-reverse gap-6 border-t border-paper/12 pt-8 sm:flex-row sm:items-center sm:justify-between">
          <p className="label text-paper/60">
            © {site.founded} {site.legalName}. All rights reserved.
          </p>
          <ul className="flex flex-wrap gap-x-6 gap-y-2">
            {legalNav.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="label text-paper/60 hover:text-paper">
                  {l.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </Container>
    </footer>
  );
}
