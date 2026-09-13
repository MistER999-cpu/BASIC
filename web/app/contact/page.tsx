import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { ContactForm } from "@/components/forms/ContactForm";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Contact",
  description:
    "Reach the studio in Amsterdam. Every message is answered by someone who has held the garment.",
  alternates: { canonical: "/contact" },
};

const CHANNELS = [
  {
    heading: "Orders & returns",
    body: "Questions about a live order, a return or an exchange. We answer within one working day.",
    action: { label: site.email, href: `mailto:${site.email}` },
  },
  {
    heading: "Sizing advice",
    body: "Tell us your usual size in a brand you know well and we will tell you honestly what to order.",
    action: { label: "Read the size guide", href: "/help/size-guide" },
  },
  {
    heading: "Repairs",
    body: "Seams, hems and buttons repaired free for as long as we make the piece. Send a photograph.",
    action: { label: site.email, href: `mailto:${site.email}` },
  },
  {
    heading: "Wholesale & press",
    body: "Line sheets, lookbook assets and sample requests for stores and publications.",
    action: { label: site.email, href: `mailto:${site.email}` },
  },
];

export default function ContactPage() {
  return (
    <>
      <PageHeader
        eyebrow="Contact"
        title="Talk to the studio"
        lede="No ticket numbers and no scripts. The person replying has the authority to fix things without asking anyone."
        crumbs={[{ label: "Home", href: "/" }, { label: "Contact" }]}
      />

      <Container className="py-16 sm:py-20">
        <div className="grid gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,26rem)] lg:gap-20">
          <div className="flex flex-col gap-10">
            <ul className="grid gap-10 sm:grid-cols-2">
              {CHANNELS.map((channel) => (
                <li key={channel.heading} className="flex flex-col gap-2 border-t border-line pt-5">
                  <h2 className="label">{channel.heading}</h2>
                  <p className="text-[0.9375rem] leading-relaxed text-ink-soft">{channel.body}</p>
                  {channel.action.href.startsWith("mailto:") ? (
                    <a
                      href={channel.action.href}
                      className="link-underline self-start text-[0.9375rem]"
                    >
                      {channel.action.label}
                    </a>
                  ) : (
                    <Link href={channel.action.href} className="link-underline self-start text-[0.9375rem]">
                      {channel.action.label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>

            <div className="flex flex-col gap-3 border-t border-line pt-5">
              <h2 className="label">Studio</h2>
              <address className="text-[0.9375rem] leading-relaxed text-ink-soft not-italic">
                {site.address.street}
                <br />
                {site.address.postalCode} {site.address.city}
                <br />
                {site.address.country}
              </address>
              <a href={`tel:${site.phone.replace(/\s/g, "")}`} className="link-underline self-start text-[0.9375rem]">
                {site.phone}
              </a>
              <p className="text-[0.8125rem] text-muted">Mon – Fri, 09:00 – 17:30 CET</p>
            </div>
          </div>

          <div className="lg:sticky lg:top-28 lg:self-start">
            <h2 className="font-display text-heading font-normal">Send a message</h2>
            <ContactForm className="mt-8" />
          </div>
        </div>
      </Container>
    </>
  );
}
