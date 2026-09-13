"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import type { Product } from "@/lib/products";
import { cn } from "@/lib/cn";
import { Price } from "./Price";
import { SaveButton } from "./SaveButton";

/**
 * Hovering the card crossfades to the second frame of the active colourway;
 * hovering a swatch switches colourway outright. Both are pure state changes,
 * so the animation pass can replace the transitions without touching logic.
 */
export function ProductCard({
  product,
  priority = false,
  sizes = "(min-width: 1280px) 25vw, (min-width: 768px) 33vw, 50vw",
  className,
}: {
  product: Product;
  priority?: boolean;
  sizes?: string;
  className?: string;
}) {
  const [colourIndex, setColourIndex] = useState(0);
  const [hovered, setHovered] = useState(false);

  const colour = product.colourways[colourIndex];
  const primary = colour.images[0];
  const secondary = colour.images[1] ?? colour.images[0];
  const href = `/shop/${product.slug}?colour=${colour.slug}`;

  return (
    <article
      className={cn("group relative flex flex-col", className)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="relative overflow-hidden bg-paper-deep">
        {/* Not a link: the title link below stretches over the whole card, so
            wrapping the image too would only add a duplicate target. */}
        <div className="relative aspect-[3/4]">
          <Image
            src={primary}
            alt={`${product.name} in ${colour.name}`}
            fill
            sizes={sizes}
            priority={priority}
            className={cn(
              "object-cover transition-opacity duration-[var(--duration-base)] ease-[var(--ease-out-quint)]",
              hovered ? "opacity-0" : "opacity-100",
            )}
          />
          <Image
            src={secondary}
            alt=""
            fill
            sizes={sizes}
            className={cn(
              "object-cover transition-[opacity,transform] duration-[var(--duration-slow)] ease-[var(--ease-out-expo)]",
              hovered ? "scale-[1.03] opacity-100" : "scale-100 opacity-0",
            )}
          />
        </div>

        {product.badge && (
          <span className="label absolute top-4 left-4 bg-paper px-2.5 py-1.5 text-ink">
            {product.badge}
          </span>
        )}

        <SaveButton
          slug={product.slug}
          name={product.name}
          className="absolute top-3 right-3 h-9 w-9 items-center justify-center bg-paper/0 opacity-0 transition-opacity duration-[var(--duration-quick)] group-hover:bg-paper/85 group-hover:opacity-100 focus-visible:bg-paper/85 focus-visible:opacity-100"
        />
      </div>

      <div className="flex flex-1 flex-col gap-2 pt-4">
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-[0.9375rem] leading-snug font-medium">
            <Link href={href} className="link-underline">
              <span className="absolute inset-0 z-10" aria-hidden />
              {product.name}
            </Link>
          </h3>
          <Price amount={product.price} compareAt={product.compareAtPrice} className="shrink-0 text-[0.9375rem]" />
        </div>

        <p className="text-[0.8125rem] text-muted">{colour.name}</p>

        {product.colourways.length > 1 && (
          <ul className="relative z-20 mt-1 flex items-center gap-2">
            {product.colourways.map((c, i) => (
              <li key={c.slug}>
                <button
                  type="button"
                  onMouseEnter={() => setColourIndex(i)}
                  onFocus={() => setColourIndex(i)}
                  onClick={() => setColourIndex(i)}
                  className={cn(
                    "block h-3.5 w-3.5 rounded-full border transition-[box-shadow,border-color] duration-[var(--duration-quick)]",
                    i === colourIndex
                      ? "border-ink ring-1 ring-ink ring-offset-2 ring-offset-paper"
                      : "border-line-strong hover:border-ink",
                  )}
                  style={{ backgroundColor: c.hex }}
                >
                  <span className="sr-only">
                    Show {product.name} in {c.name}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  );
}
