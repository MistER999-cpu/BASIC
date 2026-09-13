export type LookbookStory = {
  slug: string;
  title: string;
  season: string;
  location: string;
  credit: string;
  summary: string;
  cover: string;
  plates: { src: string; caption: string; wide?: boolean }[];
};

export const lookbook: LookbookStory[] = [
  {
    slug: "autumn-2026",
    title: "Autumn 2026",
    season: "AW26",
    location: "Amsterdam",
    credit: "Photography — Studio BASIC",
    summary:
      "Shot flat against paper over two afternoons, with no styling beyond folding. The point of the season is the rib, so we photographed the rib.",
    cover: "/editorial/range.jpg",
    plates: [
      { src: "/editorial/range.jpg", caption: "The four colourways, as they ship.", wide: true },
      { src: "/editorial/pair-light.jpg", caption: "Bone and Ink." },
      { src: "/editorial/pair-warm.jpg", caption: "Sand and Clay." },
      { src: "/textures/rib-macro.jpg", caption: "2x1 rib at 220 gsm.", wide: true },
      { src: "/products/tank-clay-neck.jpg", caption: "The mock collar, self-banded." },
      { src: "/products/tank-sand-hem.jpg", caption: "Twin-needled hem." },
    ],
  },
  {
    slug: "the-rib-study",
    title: "The Rib Study",
    season: "AW26",
    location: "Porto",
    credit: "Photography — Studio BASIC",
    summary:
      "Six frames from the knitting floor in Porto, taken while the first production run came off the machine.",
    cover: "/textures/rib-macro.jpg",
    plates: [
      { src: "/textures/rib-macro.jpg", caption: "Off the machine, before washing.", wide: true },
      { src: "/products/tank-bone-fabric.jpg", caption: "Bone, undyed base." },
      { src: "/products/tank-ink-fabric.jpg", caption: "Ink, piece-dyed." },
      { src: "/editorial/dark-still.jpg", caption: "Ink, finished.", wide: true },
    ],
  },
  {
    slug: "winter-weights",
    title: "Winter Weights",
    season: "AW26",
    location: "Biella",
    credit: "Photography — Studio BASIC",
    summary:
      "Merino from Biella and melton from Yorkshire, photographed against a warmer ground than the rest of the season.",
    cover: "/products/tone-camel.jpg",
    plates: [
      { src: "/products/tone-camel.jpg", caption: "Camel melton, 640 gsm.", wide: true },
      { src: "/products/tone-oat.jpg", caption: "Oat merino, 12 gauge." },
      { src: "/products/tone-charcoal.jpg", caption: "Charcoal merino." },
    ],
  },
];

export function getLookbookStory(slug: string) {
  return lookbook.find((s) => s.slug === slug);
}

export type JournalPost = {
  slug: string;
  title: string;
  excerpt: string;
  category: "Craft" | "Materials" | "Studio" | "Care";
  author: string;
  publishedAt: string;
  readingMinutes: number;
  cover: string;
  body: { heading?: string; paragraphs: string[] }[];
};

export const journal: JournalPost[] = [
  {
    slug: "why-we-only-make-eleven-things",
    title: "Why we only make eleven things",
    excerpt:
      "A short line is harder to design and much harder to sell. It is also the only way we know to keep quality from drifting.",
    category: "Studio",
    author: "The Studio",
    publishedAt: "2026-09-02",
    readingMinutes: 4,
    cover: "/editorial/still-wide.jpg",
    body: [
      {
        paragraphs: [
          "Most brands our size carry between eighty and two hundred styles. We carry eleven. That is not minimalism as an aesthetic — it is a constraint we adopted because we could not hold a standard across anything larger.",
          "Every style we add is another fit to re-check each season, another mill relationship to maintain, another set of grading rules that can quietly go wrong between sample and production. At eleven, one person can hold all of it in their head.",
        ],
      },
      {
        heading: "The cost of a long line",
        paragraphs: [
          "A long line looks like choice from the outside. From the inside it usually means a factory you have never visited, a fabric you accepted because the sample arrived late, and a fit you signed off on a Friday.",
          "We would rather re-cut the tank for a fourth time than release a twelfth style. The tank has been re-cut four times.",
        ],
      },
      {
        heading: "What this costs you",
        paragraphs: [
          "It means we are sometimes out of your size, and it means we will not have a version of something in the colour you want. We restock rather than replace, so the thing you bought in spring is still the thing we sell in autumn.",
        ],
      },
    ],
  },
  {
    slug: "long-staple-cotton",
    title: "What long-staple actually means",
    excerpt:
      "Staple length is the single biggest predictor of whether a cotton garment will pill. Here is the short version.",
    category: "Materials",
    author: "The Studio",
    publishedAt: "2026-08-19",
    readingMinutes: 6,
    cover: "/textures/rib-macro.jpg",
    body: [
      {
        paragraphs: [
          "A cotton fibre is a single hair. Staple length is how long that hair is before it has to be twisted into the next one. Short-staple cotton runs around 22 mm; the long-staple varieties we buy run 34 mm and above.",
          "The difference matters because every join in a yarn is a weak point and a loose end. Fewer joins means a smoother surface, which means less friction, which means less pilling.",
        ],
      },
      {
        heading: "Why it is not on most labels",
        paragraphs: [
          "There is no regulation forcing anyone to disclose staple length, so almost nobody does. '100% cotton' covers both a shirt that will look the same in five years and one that will pill across the back in five washes.",
          "We publish the staple length and the gsm on every product page for the same reason a wine label carries a region. It is the part that predicts what you actually get.",
        ],
      },
    ],
  },
  {
    slug: "a-visit-to-porto",
    title: "A visit to Porto",
    excerpt:
      "Notes from three days on the knitting floor where the rib series is made.",
    category: "Craft",
    author: "The Studio",
    publishedAt: "2026-07-28",
    readingMinutes: 5,
    cover: "/products/tank-clay-neck.jpg",
    body: [
      {
        paragraphs: [
          "The factory sits twenty minutes outside Porto in a building that has been knitting since 1974. Sixty-one people work there. We are not their largest client and we are not close to it.",
          "What we went to see was the finishing room, because that is where a rib either holds its neck or does not.",
        ],
      },
      {
        heading: "The neck",
        paragraphs: [
          "A mock neck fails in one of two ways: it stretches out and stops standing, or it is over-tightened and will not go over a head. The fix is a self-banded collar knitted on the same gauge as the body, twin-needled rather than overlocked.",
          "It takes about forty seconds longer per garment. Across a production run that is real money, which is why most mock necks are bound in a separate, cheaper tape.",
        ],
      },
    ],
  },
  {
    slug: "how-to-wash-a-rib",
    title: "How to wash a rib so it stays a rib",
    excerpt:
      "Four things that will keep a fine-gauge cotton rib looking new, and one that quietly destroys it.",
    category: "Care",
    author: "The Studio",
    publishedAt: "2026-06-30",
    readingMinutes: 3,
    cover: "/products/tank-bone-fabric.jpg",
    body: [
      {
        paragraphs: [
          "Cold water, gentle cycle, inside out, dry flat. That is the whole method and it takes no more effort than the alternative.",
          "The thing that destroys a rib is heat in the dryer. Elastane is a rubber; heat relaxes it permanently, and once the recovery is gone the neck will not stand up again. No amount of careful washing afterwards brings it back.",
        ],
      },
      {
        heading: "On washing less",
        paragraphs: [
          "Most garments are washed more often than they need to be. Airing a cotton rib overnight handles ordinary wear. Wash it when it needs washing, not on a schedule.",
        ],
      },
    ],
  },
];

export function getJournalPost(slug: string) {
  return journal.find((p) => p.slug === slug);
}

export function journalByCategory(category: string) {
  return journal.filter((p) => p.category === category);
}
