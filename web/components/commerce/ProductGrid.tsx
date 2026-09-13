import type { Product } from "@/lib/products";
import { cn } from "@/lib/cn";
import { Reveal } from "@/components/ui/Reveal";
import { ProductCard } from "./ProductCard";

export function ProductGrid({
  products,
  columns = 4,
  className,
  priorityCount = 0,
}: {
  products: Product[];
  columns?: 2 | 3 | 4;
  className?: string;
  /** How many cards opt out of lazy loading, for above-the-fold grids. */
  priorityCount?: number;
}) {
  const cols = {
    2: "grid-cols-2",
    3: "grid-cols-2 md:grid-cols-3",
    4: "grid-cols-2 md:grid-cols-3 xl:grid-cols-4",
  }[columns];

  return (
    <ul className={cn("grid gap-x-5 gap-y-12 sm:gap-x-8 sm:gap-y-16", cols, className)}>
      {products.map((product, i) => (
        <Reveal as="li" key={product.slug} delay={(i % columns) * 70}>
          <ProductCard product={product} priority={i < priorityCount} />
        </Reveal>
      ))}
    </ul>
  );
}
