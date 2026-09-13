import type { Metadata } from "next";
import { CartView } from "@/components/commerce/CartView";
import { PageHeader } from "@/components/layout/PageHeader";
import { Container } from "@/components/ui/Container";

export const metadata: Metadata = {
  title: "Bag",
  description: "Review your bag before checkout.",
  robots: { index: false, follow: false },
};

export default function CartPage() {
  return (
    <>
      <PageHeader
        eyebrow="Bag"
        title="Your bag"
        crumbs={[{ label: "Home", href: "/" }, { label: "Bag" }]}
      />
      <Container className="py-12 sm:py-16">
        <CartView />
      </Container>
    </>
  );
}
