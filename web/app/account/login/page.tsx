import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { Breadcrumbs } from "@/components/ui/Breadcrumbs";
import { AuthForm } from "@/components/forms/AuthForm";

export const metadata: Metadata = {
  title: "Sign in",
  description: "Sign in to track orders, start a return and keep your saved items across devices.",
  robots: { index: false, follow: true },
};

export default function Page() {
  return (
    <>
      <Container className="py-6 sm:py-8">
        <Breadcrumbs
          items={[
            { label: "Home", href: "/" },
            { label: "Account", href: "/account" },
            { label: "Sign in" },
          ]}
        />
      </Container>

      <Container size="narrow" className="pb-24 sm:pb-32">
        <div className="mx-auto max-w-md">
          <header className="flex flex-col gap-4 pb-10">
            <h1 className="font-display text-display font-normal">Welcome back</h1>
            <p className="text-lead text-ink-soft">Sign in to track orders, start a return and keep your saved items across devices.</p>
          </header>
          <AuthForm mode="login" />
        </div>
      </Container>
    </>
  );
}
