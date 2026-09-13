"use client";

import { useStore } from "@/components/providers/StoreProvider";
import { ButtonLink } from "@/components/ui/Button";
import { ProductCard } from "./ProductCard";
import { products } from "@/lib/products";

export function WishlistView() {
  const { wishlist, ready } = useStore();

  if (!ready) return <div className="min-h-[40vh]" aria-hidden />;

  const saved = products.filter((p) => wishlist.includes(p.slug));

  if (saved.length === 0) {
    return (
      <div className="flex min-h-[35vh] flex-col items-start justify-center gap-6">
        <p className="font-display text-title">Nothing saved yet</p>
        <p className="max-w-md text-lead text-ink-soft">
          Tap the heart on any piece to keep it here while you decide.
        </p>
        <ButtonLink href="/shop" size="lg">
          Shop everything
        </ButtonLink>
      </div>
    );
  }

  return (
    <>
      <p className="label border-b border-line pb-4 text-muted">
        {saved.length} {saved.length === 1 ? "piece" : "pieces"}
      </p>
      <ul className="mt-10 grid grid-cols-2 gap-x-5 gap-y-12 sm:gap-x-8 md:grid-cols-3 xl:grid-cols-4">
        {saved.map((product) => (
          <li key={product.slug}>
            <ProductCard product={product} />
          </li>
        ))}
      </ul>
    </>
  );
}
