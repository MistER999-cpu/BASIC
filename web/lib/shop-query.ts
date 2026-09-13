import { products, type Product } from "@/lib/products";

export type ShopQuery = {
  category?: string;
  colour?: string;
  price?: string;
  sort?: string;
  tag?: string;
};

/** Server-side filtering so /shop stays crawlable and shareable. */
export function queryProducts(query: ShopQuery, source: Product[] = products) {
  let result = [...source];

  if (query.category) {
    result = result.filter((p) => p.category === query.category);
  }

  if (query.colour) {
    result = result.filter((p) => p.colourways.some((c) => c.slug === query.colour));
  }

  if (query.price) {
    const [minRaw, maxRaw] = query.price.split("-");
    const min = Number(minRaw) || 0;
    const max = maxRaw ? Number(maxRaw) : Infinity;
    result = result.filter((p) => p.price >= min && p.price <= max);
  }

  if (query.tag === "restocked") result = result.filter((p) => p.badge === "Restocked");
  if (query.tag === "final") result = result.filter((p) => p.badge === "Final pieces");
  if (query.tag === "new") result = result.filter((p) => p.badge === "New");

  switch (query.sort) {
    case "newest":
      result.sort((a, b) => b.releasedAt.localeCompare(a.releasedAt));
      break;
    case "popular":
      result.sort((a, b) => b.popularity - a.popularity);
      break;
    case "price-asc":
      result.sort((a, b) => a.price - b.price);
      break;
    case "price-desc":
      result.sort((a, b) => b.price - a.price);
      break;
    default:
      result.sort((a, b) => Number(b.featured ?? false) - Number(a.featured ?? false) || b.popularity - a.popularity);
  }

  return result;
}
