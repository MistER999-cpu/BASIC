"use client";

import { Img as Image } from "@/components/ui/Img";
import Link from "next/link";
import { useStore } from "@/components/providers/StoreProvider";
import { Button, ButtonLink } from "@/components/ui/Button";
import { QuantityStepper } from "./QuantityStepper";
import { formatPrice } from "@/lib/format";

const FREE_SHIPPING_AT = 150;

export function CartView() {
  const { lines, subtotal, count, setQuantity, removeLine, clearCart, ready } = useStore();

  if (!ready) {
    return <div className="min-h-[40vh]" aria-hidden />;
  }

  if (lines.length === 0) {
    return (
      <div className="flex min-h-[40vh] flex-col items-start justify-center gap-6">
        <p className="font-display text-title">Your bag is empty</p>
        <p className="max-w-md text-lead text-ink-soft">
          Eleven styles, restocked rather than replaced. The rib series is the place to start.
        </p>
        <div className="flex flex-wrap gap-3">
          <ButtonLink href="/shop" size="lg">
            Shop everything
          </ButtonLink>
          <ButtonLink href="/collections/rib-series" variant="outline" size="lg">
            The Rib Series
          </ButtonLink>
        </div>
      </div>
    );
  }

  const shipping = subtotal >= FREE_SHIPPING_AT ? 0 : 9;

  return (
    <div className="grid gap-12 lg:grid-cols-[minmax(0,1fr)_22rem] lg:gap-20">
      <div>
        <div className="flex items-center justify-between border-b border-line pb-4">
          <h2 className="label">
            {count} {count === 1 ? "item" : "items"}
          </h2>
          <button
            type="button"
            onClick={clearCart}
            className="label link-underline text-muted hover:text-ink"
          >
            Empty bag
          </button>
        </div>

        <ul className="divide-y divide-line">
          {lines.map((line) => (
            <li key={line.id} className="flex gap-5 py-6 sm:gap-8">
              <Link
                href={`/shop/${line.slug}?colour=${line.colourSlug}`}
                className="relative aspect-[3/4] w-24 shrink-0 overflow-hidden bg-paper-deep sm:w-32"
              >
                <Image src={line.image} alt="" fill sizes="128px" className="object-cover" />
              </Link>

              <div className="flex min-w-0 flex-1 flex-col gap-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <h3 className="text-[0.9375rem] font-medium">
                      <Link href={`/shop/${line.slug}?colour=${line.colourSlug}`} className="link-underline">
                        {line.name}
                      </Link>
                    </h3>
                    <p className="mt-1 text-[0.8125rem] text-muted">
                      {line.colourName} · Size {line.size}
                    </p>
                  </div>
                  <span className="shrink-0 text-[0.9375rem] tabular-nums">
                    {formatPrice(line.price * line.quantity)}
                  </span>
                </div>

                <div className="mt-auto flex items-center justify-between gap-4 pt-3">
                  <QuantityStepper
                    value={line.quantity}
                    onChange={(q) => setQuantity(line.id, q)}
                    min={0}
                  />
                  <button
                    type="button"
                    onClick={() => removeLine(line.id)}
                    className="label link-underline text-muted hover:text-ink"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </li>
          ))}
        </ul>

        <Link href="/shop" className="label link-underline mt-8 inline-block">
          Continue shopping
        </Link>
      </div>

      <aside className="lg:sticky lg:top-28 lg:self-start">
        <h2 className="label border-b border-line pb-4">Summary</h2>
        <dl className="flex flex-col gap-3 py-5 text-[0.9375rem]">
          <div className="flex justify-between">
            <dt className="text-muted">Subtotal</dt>
            <dd className="tabular-nums">{formatPrice(subtotal)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Delivery</dt>
            <dd className="tabular-nums">{shipping === 0 ? "Free" : formatPrice(shipping)}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-muted">Duties</dt>
            <dd className="text-muted">Prepaid to EU, UK, US &amp; CA</dd>
          </div>
        </dl>
        <div className="flex items-baseline justify-between border-t border-ink pt-4">
          <span className="label">Total</span>
          <span className="text-lg tabular-nums">{formatPrice(subtotal + shipping)}</span>
        </div>
        <p className="mt-3 text-[0.8125rem] text-muted">
          Taxes calculated at checkout based on your delivery address.
        </p>

        <Button full size="lg" className="mt-6">
          Proceed to checkout
        </Button>
        <p className="mt-4 text-[0.8125rem] leading-relaxed text-muted">
          Checkout is not connected in this build. Wire{" "}
          <code className="text-ink">CartView</code> to your payment provider to complete it.
        </p>

        <ul className="mt-8 flex flex-col gap-2 border-t border-line pt-5 text-[0.8125rem] text-muted">
          <li>Free delivery over {formatPrice(FREE_SHIPPING_AT)}</li>
          <li>Thirty days to return, free from most markets</li>
          <li>Repairs free for as long as we make the piece</li>
        </ul>
      </aside>
    </div>
  );
}
