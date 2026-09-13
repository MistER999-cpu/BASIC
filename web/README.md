# BASIC — storefront

The website for BASIC: a short line of everyday essentials. Next.js App Router,
TypeScript, Tailwind v4. No CMS and no commerce backend yet — every page reads
from typed data in `lib/`, so the whole site renders statically and the seams
where a real backend plugs in are explicit.

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # production build
npm run lint
```

## What is here

| Route | What it is |
|---|---|
| `/` | Home — hero, press strip, signature product, new arrivals, categories, two editorial splits, lookbook, reviews, journal, newsletter |
| `/shop` | Listing with URL-driven filters (category, colour, price) and sort |
| `/shop/[slug]` | Product page — gallery, colourways, sizes, bag, accordions, related |
| `/collections`, `/collections/[slug]` | Collection index and landing pages |
| `/lookbook`, `/lookbook/[slug]` | Campaign stories and plate sequences |
| `/journal`, `/journal/[slug]` | Long-form articles |
| `/about`, `/sustainability`, `/stores`, `/careers`, `/contact` | Brand pages |
| `/help`, `/help/[slug]` | Shipping, returns, size guide, care, FAQ |
| `/legal/[slug]` | Privacy, terms, cookies, accessibility |
| `/cart`, `/wishlist`, `/account`, `/account/login`, `/account/register` | Customer pages |
| `/search` | Search results |
| `sitemap.xml`, `robots.txt` | Generated from the same data |

## Design system

Tokens live in `app/globals.css` under `@theme` — a warm-neutral palette pulled
from the garments themselves, a fluid editorial type scale, and a motion
vocabulary (`--ease-out-expo`, `--duration-*`) that the animation pass should
build on rather than replace.

Type is Instrument Serif for display and Inter for everything else, both via
`next/font`. Two house classes carry most of the character: `.label` (the
tracked uppercase micro-label) and `.link-underline`.

Every rendered text/background pair meets WCAG AA (4.5:1 body, 3:1 large).
If you change `--color-muted`, `--color-faint` or any `text-paper/NN`, re-check
it — the accessibility page makes that promise in writing.

## Motion

`components/ui/Reveal.tsx` reveals content on scroll through an
IntersectionObserver. The hiding CSS is scoped to `.js`, a class an inline
script in `app/layout.tsx` sets before first paint, so without JavaScript
everything is simply visible. `prefers-reduced-motion` disables the whole system
in `globals.css`.

When adding richer animation, prefer extending the existing tokens and the
`data-reveal` / `data-revealed` attribute contract so reduced-motion and the
no-JS path keep working for free.

## Data and images

`lib/products.ts` is the catalogue. A `Product` has one or more `Colourway`s,
each with its own image set and sold-out sizes.

The Ribbed Mock-Neck Tank ships with real photography under
`public/products/tank-*`. Every other style uses a tonal cloth card
(`public/products/tone-*`) as a stand-in until its shoot lands — replace the
`images` array for that colourway and nothing else has to change:

```ts
{ name: "Oat", slug: "oat", hex: "#D8CDBB", images: tone("oat") }
// becomes
{ name: "Oat", slug: "oat", hex: "#D8CDBB", images: [
    "/products/merino-oat.jpg",
    "/products/merino-oat-detail.jpg",
  ] }
```

A product page lays the first image out full width and the rest in two columns,
so two or four images both fill the grid cleanly; three leaves the last one
orphaned unless you let it span.

Every image in `public/` was generated from the four garment cutouts in
`../assets/products/`. Nothing is stock.

## What is not wired

Deliberate stubs, each isolated to one component:

- **Checkout** — `components/commerce/CartView.tsx`. Bag state is real and
  persists in `localStorage`; the checkout button does nothing.
- **Auth** — `components/forms/AuthForm.tsx`. Validation is real, submission is
  simulated.
- **Newsletter** — `components/ui/NewsletterForm.tsx`.
- **Contact** — `components/forms/ContactForm.tsx`.

Bag and saved items live in `components/providers/StoreProvider.tsx`, a single
reducer hydrated from `localStorage` after mount.

## Deploying

Two build modes, one codebase.

**Server build (default).** Vercel, a Node host, a container. Keeps server
rendering and on-demand image optimisation. Nothing to configure — point the
host at `web/` as the project root.

**Static export.** Any plain file host: GitHub Pages, S3, a Netlify drop.

```bash
NEXT_OUTPUT_EXPORT=1 npm run build          # writes web/out/
```

Two optional environment variables:

| Variable | When you need it |
|---|---|
| `NEXT_PUBLIC_BASE_PATH` | The site is served from a subdirectory, e.g. `/BASIC` for a GitHub project page |
| `NEXT_PUBLIC_SITE_URL` | Canonical origin for metadata, sitemap and structured data |

`public/` paths must go through `asset()` in `lib/asset.ts` — `next/image`
prefixes its own chunks with `basePath` but not the `src` of a file in
`public/`, so a subdirectory deploy would 404 on every photograph. Import
`components/ui/Img.tsx` rather than `next/image` directly and it is handled.

`.github/workflows/deploy-pages.yml` builds the export and publishes it to
GitHub Pages on every push to the default branch.

## Conventions

- Server Components by default; `"use client"` only where there is state.
- Filters and the selected colourway live in the URL, never in client state
  alone, so every view is shareable and the back button behaves.
- Structured data (`lib/jsonld.ts`) is emitted for the organisation, products,
  articles, breadcrumbs and the FAQ.
