"use client";

import Image from "next/image";
import Link from "next/link";
import { useStore } from "@/components/providers/StoreProvider";
import { Overlay } from "@/components/ui/Overlay";
import { ButtonLink } from "@/components/ui/Button";
import { QuantityStepper } from "@/components/commerce/QuantityStepper";
import { formatPrice } from "@/lib/format";

const FREE_SHIPPING_AT = 150;

export function CartDrawer() {
  const { cartOpen, setCartOpen, lines, subtotal, count, setQuantity, removeLine } = useStore();
  const remaining = Math.max(0, FREE_SHIPPING_AT - subtotal);
  const progress = Math.min(100, (subtotal / FREE_SHIPPING_AT) * 100);

  return (
    <Overlay
      open={cartOpen}
      onClose={() => setCartOpen(false)}
      label="Shopping bag"
      title={`Bag${count ? ` (${count})` : ""}`}
    >
      {lines.length === 0 ? (
        <div className="flex flex-1 flex-col items-center justify-center gap-6 px-8 text-center">
          <p className="font-display text-2xl">Your bag is empty</p>
          <p className="max-w-xs text-sm text-muted">
            Eleven styles, restocked rather than replaced. Start with the rib series.
          </p>
          <ButtonLink href="/shop" variant="outline" onClick={() => setCartOpen(false)}>
            Shop everything
          </ButtonLink>
        </div>
      ) : (
        <>
          {/* Free-shipping progress */}
          <div className="shrink-0 border-b border-line px-5 py-4 sm:px-7">
            <p className="label mb-2 text-muted">
              {remaining > 0 ? (
                <>
                  <span className="text-ink">{formatPrice(remaining)}</span> from free delivery
                </>
              ) : (
                <span className="text-success">Free delivery unlocked</span>
              )}
            </p>
            <div className="h-px w-full bg-line">
              <div
                className="h-px bg-ink transition-[width] duration-[var(--duration-slow)] ease-[var(--ease-out-expo)]"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          <ul className="flex-1 divide-y divide-line overflow-y-auto px-5 sm:px-7">
            {lines.map((line) => (
              <li key={line.id} className="flex gap-4 py-5">
                <Link
                  href={`/shop/${line.slug}?colour=${line.colourSlug}`}
                  onClick={() => setCartOpen(false)}
                  className="relative aspect-[3/4] w-20 shrink-0 overflow-hidden bg-paper-deep"
                >
                  <Image src={line.image} alt="" fill sizes="80px" className="object-cover" />
                </Link>
                <div className="flex min-w-0 flex-1 flex-col gap-1.5">
                  <div className="flex items-start justify-between gap-3">
                    <Link
                      href={`/shop/${line.slug}?colour=${line.colourSlug}`}
                      onClick={() => setCartOpen(false)}
                      className="text-sm leading-snug font-medium link-underline"
                    >
                      {line.name}
                    </Link>
                    <span className="shrink-0 text-sm tabular-nums">
                      {formatPrice(line.price * line.quantity)}
                    </span>
                  </div>
                  <p className="text-[0.8125rem] text-muted">
                    {line.colourName} · Size {line.size}
                  </p>
                  <div className="mt-auto flex items-center justify-between gap-3 pt-2">
                    <QuantityStepper
                      value={line.quantity}
                      onChange={(q) => setQuantity(line.id, q)}
                      min={0}
                      className="scale-90 origin-left"
                    />
                    <button
                      type="button"
                      onClick={() => removeLine(line.id)}
                      className="label text-muted link-underline hover:text-ink"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>

          <div className="shrink-0 border-t border-line px-5 py-5 sm:px-7">
            <div className="mb-1 flex items-baseline justify-between">
              <span className="label">Subtotal</span>
              <span className="text-lg tabular-nums">{formatPrice(subtotal)}</span>
            </div>
            <p className="mb-4 text-[0.8125rem] text-muted">
              Taxes and shipping calculated at checkout.
            </p>
            <div className="flex flex-col gap-2">
              <ButtonLink href="/cart" full onClick={() => setCartOpen(false)}>
                Checkout
              </ButtonLink>
              <ButtonLink href="/cart" variant="ghost" full onClick={() => setCartOpen(false)}>
                View bag
              </ButtonLink>
            </div>
          </div>
        </>
      )}
    </Overlay>
  );
}
