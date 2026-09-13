"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { SIZES, type Product, type Size, isSoldOut } from "@/lib/products";
import { cn } from "@/lib/cn";
import { Accordion } from "@/components/ui/Accordion";
import { Button } from "@/components/ui/Button";
import { IconCheck } from "@/components/ui/icons";
import { useStore } from "@/components/providers/StoreProvider";
import { Price } from "./Price";
import { QuantityStepper } from "./QuantityStepper";
import { Rating } from "./Rating";
import { SaveButton } from "./SaveButton";

export function ProductDetail({ product }: { product: Product }) {
  const params = useSearchParams();
  const router = useRouter();
  const { addLine } = useStore();

  const initialColour = Math.max(
    0,
    product.colourways.findIndex((c) => c.slug === params.get("colour")),
  );
  const [colourIndex, setColourIndex] = useState(initialColour);
  const [size, setSize] = useState<Size | null>(null);
  const [quantity, setQuantity] = useState(1);
  const [error, setError] = useState(false);

  const colour = product.colourways[colourIndex];

  // Keep the URL shareable as the colourway changes, without a navigation.
  useEffect(() => {
    const next = new URLSearchParams(Array.from(params.entries()));
    next.set("colour", colour.slug);
    router.replace(`?${next.toString()}`, { scroll: false });
    // `params` is a new object each render; keying on the slug is what matters.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [colour.slug]);

  const soldOutEverywhere = useMemo(
    () => SIZES.every((s) => isSoldOut(colour, s)),
    [colour],
  );

  // Images after the hero fill a two-column grid; an odd remainder leaves a hole.
  const orphanedLast = (colour.images.length - 1) % 2 === 1;

  function onAdd() {
    if (!size) {
      setError(true);
      return;
    }
    addLine(
      {
        slug: product.slug,
        name: product.name,
        colourSlug: colour.slug,
        colourName: colour.name,
        size,
        price: product.price,
        image: colour.images[0],
      },
      quantity,
    );
  }

  return (
    <div className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_26rem] lg:gap-16 xl:grid-cols-[minmax(0,1fr)_30rem]">
      {/* Gallery — scroll-snap row on small screens, stacked column on large.
          `min-w-0` matters: a grid item defaults to min-width:auto, which lets
          the horizontally scrolling row size to its content and blow out the
          document instead of scrolling inside itself. */}
      <div className="min-w-0">
        <ul className="-mx-5 flex snap-x snap-mandatory gap-2 overflow-x-auto px-5 sm:-mx-8 sm:px-8 lg:mx-0 lg:grid lg:grid-cols-2 lg:gap-2 lg:overflow-visible lg:px-0">
          {colour.images.map((src, i) => (
            <li
              key={src}
              className={cn(
                "relative aspect-[3/4] w-[84vw] shrink-0 snap-center overflow-hidden bg-paper-deep sm:w-[60vw] lg:w-auto",
                i === 0 && "lg:col-span-2 lg:aspect-[4/5]",
                // An odd number of details would leave the last one orphaned in
                // a two-column grid, so let it run full width instead.
                orphanedLast && i === colour.images.length - 1 && "lg:col-span-2 lg:aspect-[3/2]",
              )}
            >
              <Image
                src={src}
                alt={
                  i === 0
                    ? `${product.name} in ${colour.name}`
                    : `${product.name} in ${colour.name} — detail ${i}`
                }
                fill
                priority={i === 0}
                sizes="(min-width: 1024px) 45vw, 84vw"
                className="object-cover"
              />
            </li>
          ))}
        </ul>
      </div>

      {/* Purchase panel */}
      <div className="min-w-0 lg:sticky lg:top-28 lg:self-start">
        <div className="flex flex-col gap-6">
          <div className="flex flex-col gap-3">
            {product.badge && <span className="label text-clay">{product.badge}</span>}
            <h1 className="font-display text-heading font-normal">{product.name}</h1>
            <p className="text-lead text-ink-soft">{product.tagline}</p>
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
              <Price amount={product.price} compareAt={product.compareAtPrice} className="text-lg" />
              <Rating value={product.rating.value} count={product.rating.count} />
            </div>
          </div>

          <hr className="border-line" />

          {/* Colourway */}
          <fieldset className="flex flex-col gap-3">
            <legend className="label mb-3 text-muted">
              Colour — <span className="text-ink">{colour.name}</span>
            </legend>
            <div className="flex flex-wrap items-center gap-3">
              {product.colourways.map((c, i) => (
                <button
                  key={c.slug}
                  type="button"
                  onClick={() => {
                    setColourIndex(i);
                    setSize(null);
                  }}
                  aria-pressed={i === colourIndex}
                  className={cn(
                    "h-8 w-8 rounded-full border transition-[box-shadow,border-color] duration-[var(--duration-quick)]",
                    i === colourIndex
                      ? "border-ink ring-1 ring-ink ring-offset-3 ring-offset-paper"
                      : "border-line-strong hover:border-ink",
                  )}
                  style={{ backgroundColor: c.hex }}
                >
                  <span className="sr-only">{c.name}</span>
                </button>
              ))}
            </div>
          </fieldset>

          {/* Size */}
          <fieldset className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
              <legend className="label text-muted">Size</legend>
              <Link href="/help/size-guide" className="label link-underline text-muted hover:text-ink">
                Size guide
              </Link>
            </div>
            <div className="grid grid-cols-5 gap-2">
              {SIZES.map((s) => {
                const out = isSoldOut(colour, s);
                const selected = size === s;
                return (
                  <button
                    key={s}
                    type="button"
                    disabled={out}
                    aria-pressed={selected}
                    onClick={() => {
                      setSize(s);
                      setError(false);
                    }}
                    className={cn(
                      "label relative h-12 border transition-colors duration-[var(--duration-quick)]",
                      selected
                        ? "border-ink bg-ink text-paper"
                        : "border-line-strong text-ink hover:border-ink",
                      out &&
                        "cursor-not-allowed border-line text-faint hover:border-line " +
                          "after:absolute after:inset-x-2 after:top-1/2 after:h-px after:bg-current after:opacity-50",
                    )}
                  >
                    {s}
                    {out && <span className="sr-only"> — sold out</span>}
                  </button>
                );
              })}
            </div>
            {error && (
              <p role="alert" className="label text-danger">
                Please choose a size.
              </p>
            )}
          </fieldset>

          {/* Buy */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <QuantityStepper value={quantity} onChange={setQuantity} />
              <Button onClick={onAdd} disabled={soldOutEverywhere} className="h-11 flex-1">
                {soldOutEverywhere ? "Sold out" : "Add to bag"}
              </Button>
            </div>
            <div className="flex items-center justify-between">
              <SaveButton slug={product.slug} name={product.name} withLabel />
              <p className="label flex items-center gap-2 text-muted">
                <IconCheck className="text-success" />
                Free delivery over €150
              </p>
            </div>
          </div>

          <p className="text-[0.9375rem] leading-relaxed text-ink-soft">{product.description}</p>

          <Accordion
            className="mt-2"
            defaultOpen={0}
            headingLevel={2}
            items={[
              {
                title: "Details & fit",
                content: (
                  <div className="flex flex-col gap-4">
                    <ul className="flex list-disc flex-col gap-1.5 pl-4">
                      {product.details.map((d) => (
                        <li key={d}>{d}</li>
                      ))}
                    </ul>
                    <p>{product.fit}</p>
                  </div>
                ),
              },
              {
                title: "Fabric & origin",
                content: (
                  <dl className="grid grid-cols-[8rem_1fr] gap-x-6 gap-y-2">
                    <dt className="label text-muted">Composition</dt>
                    <dd>{product.composition}</dd>
                    <dt className="label text-muted">Weight</dt>
                    <dd>{product.weight}</dd>
                    <dt className="label text-muted">Origin</dt>
                    <dd>{product.madeIn}</dd>
                  </dl>
                ),
              },
              {
                title: "Care",
                content: (
                  <ul className="flex list-disc flex-col gap-1.5 pl-4">
                    {product.care.map((c) => (
                      <li key={c}>{c}</li>
                    ))}
                  </ul>
                ),
              },
              {
                title: "Shipping & returns",
                content: (
                  <div className="flex flex-col gap-3">
                    <p>
                      Dispatched from Amsterdam within one working day. Free delivery over €150,
                      duties prepaid to the EU, UK, US and Canada.
                    </p>
                    <p>
                      Thirty days to return, free from most markets.{" "}
                      <Link href="/help/returns" className="link-underline">
                        Read the returns policy
                      </Link>
                      .
                    </p>
                  </div>
                ),
              },
            ]}
          />
        </div>
      </div>
    </div>
  );
}
