export type Collection = {
  slug: string;
  name: string;
  season: string;
  tagline: string;
  description: string;
  image: string;
  portrait: string;
  order: number;
};

export const collections: Collection[] = [
  {
    slug: "rib-series",
    name: "The Rib Series",
    season: "Autumn 2026",
    tagline: "One rib, four colourways, cut two ways.",
    description:
      "The series began as a single tank the studio could not stop reordering. We took the rib it was knitted from, held the gauge, and built a short family around it — a mock neck, a long sleeve, and the four colours that make up the rest of the range. Nothing else was added.",
    image: "/editorial/range.jpg",
    portrait: "/products/tank-clay.jpg",
    order: 1,
  },
  {
    slug: "core",
    name: "Core Essentials",
    season: "Permanent",
    tagline: "The pieces that never leave the line.",
    description:
      "Eleven styles that stay in stock year-round, re-cut only when a mill changes or a fit is genuinely improved. If you buy one thing from BASIC, buy it from here — it will still be here when you need another.",
    image: "/editorial/still-wide.jpg",
    portrait: "/editorial/pair-light.jpg",
    order: 2,
  },
  {
    slug: "winter-weights",
    name: "Winter Weights",
    season: "Autumn 2026",
    tagline: "Merino, cashmere and a coat that earns its keep.",
    description:
      "Heavier cloth, tighter gauges, and the melton overcoat we mill in Yorkshire. Built for the four months of the year when a garment has an actual job to do.",
    image: "/products/tone-camel.jpg",
    portrait: "/products/tone-charcoal.jpg",
    order: 3,
  },
  {
    slug: "neutrals",
    name: "The Neutrals",
    season: "Permanent",
    tagline: "Bone, sand, oat, clay, ink.",
    description:
      "Every colour we hold, gathered in one place. The palette is deliberately short so that anything bought two years apart still sits together.",
    image: "/editorial/pair-warm.jpg",
    portrait: "/products/tank-sand.jpg",
    order: 4,
  },
  {
    slug: "layering",
    name: "The Layering Edit",
    season: "Permanent",
    tagline: "What goes under, and what goes over.",
    description:
      "Cut and weighted to stack without bulk — flat seams, narrow cuffs, and hems that sit clear of each other.",
    image: "/editorial/dark-still.jpg",
    portrait: "/products/tone-slate.jpg",
    order: 5,
  },
];

export function getCollection(slug: string) {
  return collections.find((c) => c.slug === slug);
}
