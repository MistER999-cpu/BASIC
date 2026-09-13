import type { Metadata } from "next";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { ButtonLink } from "@/components/ui/Button";
import { IconArrowRight } from "@/components/ui/icons";

export const metadata: Metadata = {
  title: "Account",
  description: "Sign in to track orders, start a return and keep your saved items across devices.",
  robots: { index: false, follow: true },
};

const PANELS = [
  { title: "Orders", body: "Track a live order or download an invoice.", href: "/account/login" },
  { title: "Returns", body: "Start a return or an exchange in two minutes.", href: "/help/returns" },
  { title: "Addresses", body: "Manage delivery and billing addresses.", href: "/account/login" },
  { title: "Saved items", body: "Keep pieces across devices, not just this browser.", href: "/wishlist" },
];

export default function AccountPage() {
  return (
    <>
      <PageHeader
        eyebrow="Account"
        title="Your account"
        lede="Sign in to track orders, start a return, and keep saved items across devices."
        crumbs={[{ label: "Home", href: "/" }, { label: "Account" }]}
      />

      <Container className="py-14 sm:py-20">
        <div className="grid gap-14 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)] lg:gap-20">
          <ul className="grid gap-8 sm:grid-cols-2">
            {PANELS.map((panel) => (
              <li key={panel.title}>
                <Link href={panel.href} className="group flex flex-col gap-2 border-t border-line pt-5">
                  <h2 className="font-display text-2xl leading-tight">
                    <span className="link-underline">{panel.title}</span>
                  </h2>
                  <p className="text-[0.9375rem] text-muted">{panel.body}</p>
                  <IconArrowRight className="mt-2 text-muted transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)] group-hover:translate-x-1 group-hover:text-ink" />
                </Link>
              </li>
            ))}
          </ul>

          <aside className="flex flex-col gap-5 border-t border-line pt-5 lg:border-0 lg:pt-0">
            <h2 className="font-display text-heading font-normal">Not signed in</h2>
            <p className="text-[0.9375rem] leading-relaxed text-ink-soft">
              You can order as a guest — an account only exists so you do not have to type your
              address twice.
            </p>
            <div className="flex flex-col gap-3">
              <ButtonLink href="/account/login" full>
                Sign in
              </ButtonLink>
              <ButtonLink href="/account/register" variant="outline" full>
                Create an account
              </ButtonLink>
            </div>
          </aside>
        </div>
      </Container>
    </>
  );
}
