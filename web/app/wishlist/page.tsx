import type { Metadata } from "next";
import { Container } from "@/components/ui/Container";
import { PageHeader } from "@/components/layout/PageHeader";
import { WishlistView } from "@/components/commerce/WishlistView";

export const metadata: Metadata = {
  title: "Saved items",
  description: "Pieces you have saved for later.",
  robots: { index: false, follow: true },
};

export default function WishlistPage() {
  return (
    <>
      <PageHeader
        eyebrow="Saved"
        title="Saved items"
        lede="Saved to this browser. Create an account to keep them across devices."
        crumbs={[{ label: "Home", href: "/" }, { label: "Saved items" }]}
      />
      <Container className="py-12 sm:py-16">
        <WishlistView />
      </Container>
    </>
  );
}
