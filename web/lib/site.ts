export type NavLink = {
  label: string;
  href: string;
  description?: string;
};

export type NavGroup = {
  heading: string;
  links: NavLink[];
};

export type NavItem = {
  label: string;
  href: string;
  /** Columns rendered in the desktop mega-menu. */
  groups?: NavGroup[];
  /** Optional visual promo shown alongside the columns. */
  feature?: {
    href: string;
    image: string;
    eyebrow: string;
    title: string;
  };
};

export const site = {
  name: "BASIC",
  legalName: "Basic Studio B.V.",
  tagline: "The essentials, considered.",
  description:
    "BASIC makes a short, deliberate wardrobe of everyday essentials — cut from long-staple cotton and merino, made in limited runs, and designed to be worn until they wear out.",
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "https://basic.studio",
  founded: 2026,
  email: "studio@basic.studio",
  phone: "+31 20 123 4567",
  address: {
    street: "Keizersgracht 241",
    postalCode: "1016 EA",
    city: "Amsterdam",
    country: "Netherlands",
  },
  socials: [
    { label: "Instagram", href: "https://instagram.com" },
    { label: "Pinterest", href: "https://pinterest.com" },
    { label: "TikTok", href: "https://tiktok.com" },
    { label: "Spotify", href: "https://spotify.com" },
  ],
  announcements: [
    "Complimentary shipping on orders over €150",
    "The Rib Series — four colourways, now in stock",
    "Free returns within 30 days, worldwide",
  ],
} as const;

export const mainNav: NavItem[] = [
  {
    label: "Shop",
    href: "/shop",
    groups: [
      {
        heading: "Category",
        links: [
          { label: "All ready-to-wear", href: "/shop" },
          { label: "Tops", href: "/shop?category=tops" },
          { label: "Knitwear", href: "/shop?category=knitwear" },
          { label: "Bottoms", href: "/shop?category=bottoms" },
          { label: "Outerwear", href: "/shop?category=outerwear" },
          { label: "Dresses", href: "/shop?category=dresses" },
          { label: "Accessories", href: "/shop?category=accessories" },
        ],
      },
      {
        heading: "Collections",
        links: [
          { label: "The Rib Series", href: "/collections/rib-series" },
          { label: "Core Essentials", href: "/collections/core" },
          { label: "Winter Weights", href: "/collections/winter-weights" },
          { label: "The Neutrals", href: "/collections/neutrals" },
          { label: "View all", href: "/collections" },
        ],
      },
      {
        heading: "Find",
        links: [
          { label: "New arrivals", href: "/shop?sort=newest" },
          { label: "Best sellers", href: "/shop?sort=popular" },
          { label: "Back in stock", href: "/shop?tag=restocked" },
          { label: "Last pieces", href: "/shop?tag=final" },
          { label: "Gift cards", href: "/shop?category=accessories" },
        ],
      },
    ],
    feature: {
      href: "/shop/ribbed-mock-neck-tank",
      image: "/products/tank-clay.jpg",
      eyebrow: "Signature",
      title: "The Ribbed Mock-Neck Tank",
    },
  },
  {
    label: "Collections",
    href: "/collections",
    groups: [
      {
        heading: "Seasonal",
        links: [
          { label: "The Rib Series", href: "/collections/rib-series" },
          { label: "Winter Weights", href: "/collections/winter-weights" },
          { label: "The Neutrals", href: "/collections/neutrals" },
        ],
      },
      {
        heading: "Permanent",
        links: [
          { label: "Core Essentials", href: "/collections/core" },
          { label: "The Layering Edit", href: "/collections/layering" },
        ],
      },
    ],
    feature: {
      href: "/collections/rib-series",
      image: "/editorial/range.jpg",
      eyebrow: "Collection",
      title: "The Rib Series",
    },
  },
  {
    label: "Lookbook",
    href: "/lookbook",
  },
  {
    label: "Journal",
    href: "/journal",
  },
  {
    label: "About",
    href: "/about",
    groups: [
      {
        heading: "The studio",
        links: [
          { label: "Our story", href: "/about" },
          { label: "Materials & responsibility", href: "/sustainability" },
          { label: "Stockists", href: "/stores" },
          { label: "Careers", href: "/careers" },
          { label: "Contact", href: "/contact" },
        ],
      },
    ],
  },
];

export const footerNav: NavGroup[] = [
  {
    heading: "Shop",
    links: [
      { label: "All ready-to-wear", href: "/shop" },
      { label: "New arrivals", href: "/shop?sort=newest" },
      { label: "Collections", href: "/collections" },
      { label: "Lookbook", href: "/lookbook" },
      { label: "Gift cards", href: "/shop?category=accessories" },
    ],
  },
  {
    heading: "Help",
    links: [
      { label: "Shipping & delivery", href: "/help/shipping" },
      { label: "Returns & exchanges", href: "/help/returns" },
      { label: "Size guide", href: "/help/size-guide" },
      { label: "Garment care", href: "/help/care" },
      { label: "FAQ", href: "/help/faq" },
    ],
  },
  {
    heading: "Studio",
    links: [
      { label: "Our story", href: "/about" },
      { label: "Materials", href: "/sustainability" },
      { label: "Journal", href: "/journal" },
      { label: "Stockists", href: "/stores" },
      { label: "Careers", href: "/careers" },
    ],
  },
  {
    heading: "Account",
    links: [
      { label: "Sign in", href: "/account/login" },
      { label: "Create account", href: "/account/register" },
      { label: "Saved items", href: "/wishlist" },
      { label: "Bag", href: "/cart" },
      { label: "Contact us", href: "/contact" },
    ],
  },
];

export const legalNav: NavLink[] = [
  { label: "Privacy", href: "/legal/privacy" },
  { label: "Terms", href: "/legal/terms" },
  { label: "Cookies", href: "/legal/cookies" },
  { label: "Accessibility", href: "/legal/accessibility" },
];
