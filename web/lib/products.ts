/**
 * The catalogue.
 *
 * The Ribbed Mock-Neck Tank is the house signature and ships with real
 * photography (`/products/tank-*`). Every other style is written against the
 * same shape and uses tonal cloth cards (`/products/tone-*`) until its shoot
 * lands — swap the `images` arrays and nothing else has to change.
 */

export const SIZES = ["XS", "S", "M", "L", "XL"] as const;
export type Size = (typeof SIZES)[number];

export type CategorySlug =
  | "tops"
  | "knitwear"
  | "bottoms"
  | "outerwear"
  | "dresses"
  | "accessories";

export type Category = {
  slug: CategorySlug;
  name: string;
  blurb: string;
  image: string;
};

export const categories: Category[] = [
  { slug: "tops", name: "Tops", blurb: "Ribs, jersey and the everyday layer.", image: "/products/tank-clay.jpg" },
  { slug: "knitwear", name: "Knitwear", blurb: "Merino and cashmere, held to weight.", image: "/products/tone-oat.jpg" },
  { slug: "bottoms", name: "Bottoms", blurb: "Trousers cut for line, not for trend.", image: "/products/tone-ink.jpg" },
  { slug: "outerwear", name: "Outerwear", blurb: "Coats built to outlast the season.", image: "/products/tone-camel.jpg" },
  { slug: "dresses", name: "Dresses", blurb: "One silhouette, done properly.", image: "/products/tone-espresso.jpg" },
  { slug: "accessories", name: "Accessories", blurb: "The last ten percent.", image: "/products/tone-sand.jpg" },
];

export type Colourway = {
  name: string;
  slug: string;
  hex: string;
  images: string[];
  /** Sizes that are out of stock in this colourway. */
  soldOut?: Size[];
};

export type ProductBadge = "New" | "Restocked" | "Final pieces";

export type Product = {
  slug: string;
  name: string;
  tagline: string;
  price: number;
  compareAtPrice?: number;
  category: CategorySlug;
  collections: string[];
  badge?: ProductBadge;
  releasedAt: string;
  popularity: number;
  featured?: boolean;
  description: string;
  details: string[];
  composition: string;
  weight: string;
  fit: string;
  care: string[];
  madeIn: string;
  rating: { value: number; count: number };
  colourways: Colourway[];
};

const tone = (name: string) => [
  `/products/tone-${name}.jpg`,
  `/products/tone-${name}-detail.jpg`,
  `/products/tone-${name}-sq.jpg`,
];

const tank = (colour: string) => [
  `/products/tank-${colour}.jpg`,
  `/products/tank-${colour}-neck.jpg`,
  `/products/tank-${colour}-fabric.jpg`,
  `/products/tank-${colour}-hem.jpg`,
];

export const products: Product[] = [
  {
    slug: "ribbed-mock-neck-tank",
    name: "The Ribbed Mock-Neck Tank",
    tagline: "A high neck, a clean shoulder, four ways to wear it.",
    price: 68,
    category: "tops",
    collections: ["rib-series", "core", "neutrals"],
    badge: "New",
    releasedAt: "2026-08-14",
    popularity: 98,
    featured: true,
    description:
      "The piece the studio keeps coming back to. A fine 2x1 rib knitted to hold its shape at the neck, with a mock collar that sits just high enough to read deliberate. The armhole is cut close and finished flat so it layers under tailoring without bulk, and the body skims rather than clings.",
    details: [
      "Mock neck, self-banded and twin-needled",
      "Close-cut armhole with a flat-finished binding",
      "Straight body with a marginally dropped back hem",
      "Pre-shrunk — it will not move after the first wash",
    ],
    composition: "94% long-staple organic cotton, 6% elastane",
    weight: "220 gsm",
    fit: "Close fit. Take your usual size; size up for a relaxed line.",
    care: [
      "Machine wash cold on a gentle cycle",
      "Wash with like colours, inside out",
      "Dry flat in shade — do not tumble dry",
      "Warm iron on the reverse if needed",
    ],
    madeIn: "Knitted and sewn in Porto, Portugal",
    rating: { value: 4.8, count: 214 },
    colourways: [
      { name: "Bone", slug: "bone", hex: "#F2EFE9", images: tank("bone") },
      { name: "Ink", slug: "ink", hex: "#191614", images: tank("ink"), soldOut: ["XS"] },
      { name: "Clay", slug: "clay", hex: "#6B4A34", images: tank("clay") },
      { name: "Sand", slug: "sand", hex: "#CBB99E", images: tank("sand"), soldOut: ["XL"] },
    ],
  },
  {
    slug: "cotton-rib-long-sleeve",
    name: "The Cotton Rib Long-Sleeve",
    tagline: "The tank, with sleeves and a longer line.",
    price: 88,
    category: "tops",
    collections: ["rib-series", "core", "layering"],
    releasedAt: "2026-08-14",
    popularity: 84,
    featured: true,
    description:
      "Built on the same rib as the tank, extended into a long sleeve that finishes past the wrist bone. The cuff is knitted narrow so it stays put under a coat, and the body runs two centimetres longer for tucking.",
    details: [
      "Matched 2x1 rib, knitted on the same gauge as the tank",
      "Narrow cuff that holds without gripping",
      "Set-in sleeve for a clean shoulder line",
    ],
    composition: "94% long-staple organic cotton, 6% elastane",
    weight: "230 gsm",
    fit: "Close fit with a long body. True to size.",
    care: [
      "Machine wash cold on a gentle cycle",
      "Dry flat in shade",
      "Do not bleach",
    ],
    madeIn: "Knitted and sewn in Porto, Portugal",
    rating: { value: 4.7, count: 132 },
    colourways: [
      { name: "Ink", slug: "ink", hex: "#1A1614", images: tone("ink") },
      { name: "Bone", slug: "bone", hex: "#EFE9E0", images: tone("bone") },
      { name: "Clay", slug: "clay", hex: "#6B4A34", images: tone("clay"), soldOut: ["S"] },
    ],
  },
  {
    slug: "merino-crew",
    name: "The Merino Crew",
    tagline: "Fine-gauge merino that behaves like a shirt.",
    price: 185,
    category: "knitwear",
    collections: ["winter-weights", "core", "layering"],
    releasedAt: "2026-07-02",
    popularity: 91,
    featured: true,
    description:
      "Extra-fine merino spun in Biella and knitted at a gauge tight enough to wear alone. The crew sits flat against the collarbone, the ribbing is short and firm, and the whole thing packs down to nothing.",
    details: [
      "18.5 micron extra-fine merino",
      "Fully fashioned — shaped on the machine, not cut from panel",
      "Short, firm rib at the neck, cuff and hem",
    ],
    composition: "100% extra-fine merino wool",
    weight: "12 gauge",
    fit: "Regular fit, slightly tapered through the body.",
    care: [
      "Hand wash cool or use a wool cycle",
      "Reshape and dry flat",
      "Store folded, never hung",
    ],
    madeIn: "Knitted in Biella, Italy",
    rating: { value: 4.9, count: 176 },
    colourways: [
      { name: "Oat", slug: "oat", hex: "#D8CDBB", images: tone("oat") },
      { name: "Charcoal", slug: "charcoal", hex: "#3A3633", images: tone("charcoal") },
    ],
  },
  {
    slug: "boxy-tee",
    name: "The Boxy Tee",
    tagline: "A square cut in heavy jersey.",
    price: 55,
    category: "tops",
    collections: ["core", "neutrals"],
    badge: "Restocked",
    releasedAt: "2026-05-20",
    popularity: 88,
    description:
      "Cut square through the body with a shoulder that sits just off the joint. Heavy enough to hang cleanly and hold a hem, washed once before it leaves the factory so it arrives already settled.",
    details: [
      "Boxy body, dropped shoulder",
      "Ribbed neck with a taped back seam",
      "Garment-washed for a settled hand",
    ],
    composition: "100% organic cotton",
    weight: "240 gsm",
    fit: "Boxy. Size down for a closer line.",
    care: ["Machine wash cold", "Tumble dry low", "Warm iron"],
    madeIn: "Sewn in Porto, Portugal",
    rating: { value: 4.6, count: 309 },
    colourways: [
      { name: "Bone", slug: "bone", hex: "#EFE9E0", images: tone("bone") },
      { name: "Ink", slug: "ink", hex: "#1A1614", images: tone("ink") },
      { name: "Sage", slug: "sage", hex: "#9BA391", images: tone("sage") },
    ],
  },
  {
    slug: "wide-leg-trouser",
    name: "The Wide-Leg Trouser",
    tagline: "A full leg that keeps its crease.",
    price: 165,
    category: "bottoms",
    collections: ["core", "winter-weights"],
    releasedAt: "2026-06-11",
    popularity: 79,
    featured: true,
    description:
      "A high, clean waist running into a full leg that breaks once over the shoe. Cut from a dry-handle wool blend chosen because it holds a crease through a day of sitting down.",
    details: [
      "High waist with a hidden hook closure",
      "Pressed crease front and back",
      "Deep side pockets, single welt at the rear",
    ],
    composition: "78% virgin wool, 20% viscose, 2% elastane",
    weight: "290 gsm",
    fit: "High-waisted, wide through the leg. True to size.",
    care: ["Dry clean only", "Press on the reverse under a cloth"],
    madeIn: "Tailored in Vicenza, Italy",
    rating: { value: 4.7, count: 98 },
    colourways: [
      { name: "Ink", slug: "ink", hex: "#1A1614", images: tone("ink") },
      { name: "Stone", slug: "stone", hex: "#A8A096", images: tone("stone") },
    ],
  },
  {
    slug: "tailored-trouser",
    name: "The Tailored Trouser",
    tagline: "Straight, flat-fronted, quietly formal.",
    price: 195,
    category: "bottoms",
    collections: ["core"],
    releasedAt: "2026-04-28",
    popularity: 72,
    description:
      "The narrower answer to the wide leg. Flat-fronted, straight from knee to hem, and finished with a half-lining so it moves without clinging.",
    details: [
      "Flat front, straight leg",
      "Half-lined to the knee",
      "Extended waistband tab",
    ],
    composition: "82% virgin wool, 18% polyamide",
    weight: "270 gsm",
    fit: "Regular fit, straight leg.",
    care: ["Dry clean only"],
    madeIn: "Tailored in Vicenza, Italy",
    rating: { value: 4.5, count: 64 },
    colourways: [{ name: "Charcoal", slug: "charcoal", hex: "#3A3633", images: tone("charcoal") }],
  },
  {
    slug: "cashmere-scarf",
    name: "The Cashmere Scarf",
    tagline: "Two metres of Inner Mongolian cashmere.",
    price: 140,
    category: "accessories",
    collections: ["winter-weights", "neutrals"],
    releasedAt: "2026-09-01",
    popularity: 81,
    description:
      "Long enough to double and still hang. Knitted from grade-A cashmere with a hand-finished fringe, brushed lightly so it softens rather than sheds.",
    details: ["200 x 35 cm", "Hand-knotted fringe", "Lightly brushed finish"],
    composition: "100% grade-A cashmere",
    weight: "7 gauge",
    fit: "One size.",
    care: ["Hand wash cool", "Dry flat", "De-pill by hand as needed"],
    madeIn: "Knitted in Hawick, Scotland",
    rating: { value: 4.9, count: 121 },
    colourways: [
      { name: "Oat", slug: "oat", hex: "#D8CDBB", images: tone("oat") },
      { name: "Espresso", slug: "espresso", hex: "#3D2B20", images: tone("espresso") },
    ],
  },
  {
    slug: "wool-overcoat",
    name: "The Wool Overcoat",
    tagline: "A single-breasted coat with a long line.",
    price: 520,
    compareAtPrice: 620,
    category: "outerwear",
    collections: ["winter-weights"],
    badge: "Final pieces",
    releasedAt: "2026-03-15",
    popularity: 86,
    featured: true,
    description:
      "Cut long and narrow through the shoulder so it reads as a coat rather than a wrap. The cloth is a wool-cashmere melton milled in Yorkshire, dense enough to hold the line without a heavy interlining.",
    details: [
      "Single-breasted, three-button front",
      "Notched lapel with a hand-padded collar",
      "Fully lined in cupro",
      "Deep welt pockets and an interior chest pocket",
    ],
    composition: "90% virgin wool, 10% cashmere. Lining: 100% cupro",
    weight: "640 gsm melton",
    fit: "Regular fit, cut to layer over knitwear.",
    care: ["Dry clean only", "Brush after wear", "Store on a broad hanger"],
    madeIn: "Made in Yorkshire, England",
    rating: { value: 4.8, count: 57 },
    colourways: [
      { name: "Camel", slug: "camel", hex: "#B08A5E", images: tone("camel") },
      { name: "Ink", slug: "ink", hex: "#1A1614", images: tone("ink"), soldOut: ["XS", "S"] },
    ],
  },
  {
    slug: "silk-slip-dress",
    name: "The Silk Slip Dress",
    tagline: "Bias-cut sandwashed silk.",
    price: 240,
    category: "dresses",
    collections: ["core", "neutrals"],
    releasedAt: "2026-06-30",
    popularity: 77,
    description:
      "Cut on the true bias so it falls rather than hangs. Sandwashed silk takes the shine off and gives the cloth enough weight to move with you.",
    details: [
      "True bias cut",
      "Adjustable strap with a covered slider",
      "French seams throughout",
    ],
    composition: "100% sandwashed mulberry silk",
    weight: "19 momme",
    fit: "Skims the body. Take your usual size.",
    care: ["Dry clean, or hand wash cool with a silk detergent", "Dry flat in shade"],
    madeIn: "Sewn in Como, Italy",
    rating: { value: 4.6, count: 88 },
    colourways: [
      { name: "Bone", slug: "bone", hex: "#EFE9E0", images: tone("bone") },
      { name: "Espresso", slug: "espresso", hex: "#3D2B20", images: tone("espresso") },
    ],
  },
  {
    slug: "denim-jacket",
    name: "The Denim Jacket",
    tagline: "Rigid selvedge, cut boxy.",
    price: 210,
    category: "outerwear",
    collections: ["core", "layering"],
    releasedAt: "2026-02-10",
    popularity: 68,
    description:
      "Fourteen-ounce rigid selvedge from Okayama, cut square and left raw so it takes its shape from the person wearing it. Expect it to be stiff for a month and yours after that.",
    details: [
      "14 oz rigid selvedge denim",
      "Boxy body, squared shoulder",
      "Copper rivets and a chain-stitched hem",
    ],
    composition: "100% cotton selvedge denim",
    weight: "14 oz",
    fit: "Boxy. Size down if you want it close.",
    care: ["Wash rarely, cold, inside out", "Hang to dry", "Expect indigo to transfer at first"],
    madeIn: "Woven in Okayama, Japan. Sewn in Portugal.",
    rating: { value: 4.7, count: 143 },
    colourways: [{ name: "Indigo", slug: "indigo", hex: "#33405A", images: tone("indigo") }],
  },
  {
    slug: "everyday-tote",
    name: "The Everyday Tote",
    tagline: "Structured canvas with a leather base.",
    price: 185,
    category: "accessories",
    collections: ["core", "neutrals"],
    releasedAt: "2026-05-05",
    popularity: 74,
    description:
      "Heavy cotton canvas with a vegetable-tanned base that takes the wear. Squared off so it stands up on its own when you put it down.",
    details: [
      "18 oz cotton canvas with a leather base",
      "Interior zip pocket and two slip pockets",
      "Handles long enough for the shoulder",
    ],
    composition: "18 oz cotton canvas, vegetable-tanned leather trim",
    weight: "0.9 kg",
    fit: "38 x 34 x 14 cm.",
    care: ["Spot clean only", "Condition the leather trim annually"],
    madeIn: "Made in Tuscany, Italy",
    rating: { value: 4.7, count: 52 },
    colourways: [{ name: "Sand", slug: "sand", hex: "#CBB99E", images: tone("sand") }],
  },
];

/* ------------------------------------------------------------------ queries */

export function getProduct(slug: string) {
  return products.find((p) => p.slug === slug);
}

export function getCategory(slug: string) {
  return categories.find((c) => c.slug === slug);
}

export function productsByCollection(collection: string) {
  return products.filter((p) => p.collections.includes(collection));
}

export function featuredProducts() {
  return products.filter((p) => p.featured);
}

export function relatedProducts(product: Product, limit = 4) {
  const sameCollection = products.filter(
    (p) => p.slug !== product.slug && p.collections.some((c) => product.collections.includes(c)),
  );
  const rest = products.filter(
    (p) => p.slug !== product.slug && !sameCollection.includes(p),
  );
  return [...sameCollection, ...rest].slice(0, limit);
}

export function priceRange() {
  const values = products.map((p) => p.price);
  return { min: Math.min(...values), max: Math.max(...values) };
}

/** Every colour name in the catalogue, for the shop filter rail. */
export function allColours() {
  const seen = new Map<string, { name: string; slug: string; hex: string }>();
  for (const product of products) {
    for (const colour of product.colourways) {
      if (!seen.has(colour.slug)) {
        seen.set(colour.slug, { name: colour.name, slug: colour.slug, hex: colour.hex });
      }
    }
  }
  return [...seen.values()].sort((a, b) => a.name.localeCompare(b.name));
}

export function searchProducts(query: string) {
  const q = query.trim().toLowerCase();
  if (!q) return [];
  return products.filter((p) =>
    [p.name, p.tagline, p.description, p.category, ...p.colourways.map((c) => c.name)]
      .join(" ")
      .toLowerCase()
      .includes(q),
  );
}

export function isSoldOut(colour: Colourway, size: Size) {
  return colour.soldOut?.includes(size) ?? false;
}
