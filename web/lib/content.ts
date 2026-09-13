export type Section = { heading?: string; paragraphs?: string[]; list?: string[] };

export type Doc = {
  slug: string;
  title: string;
  summary: string;
  updatedAt: string;
  sections: Section[];
};

/* ------------------------------------------------------------- help centre */

export const helpDocs: Doc[] = [
  {
    slug: "shipping",
    title: "Shipping & delivery",
    summary: "Where we ship, what it costs, and how long it takes.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: [
          "Orders placed before 14:00 CET on a working day leave the Amsterdam studio the same day. Everything ships tracked, and you will get the tracking number by email the moment the parcel is scanned.",
        ],
      },
      {
        heading: "Rates and times",
        list: [
          "Netherlands & Belgium — €5, or free over €150. 1–2 working days.",
          "European Union — €9, or free over €150. 2–4 working days.",
          "United Kingdom — €12, or free over €200. 3–5 working days. Duties prepaid.",
          "United States & Canada — €18, or free over €250. 4–7 working days. Duties prepaid.",
          "Rest of world — €26. 6–12 working days. Duties payable on receipt.",
        ],
      },
      {
        heading: "Duties and taxes",
        paragraphs: [
          "For the EU, UK, US and Canada we prepay duties and import tax, so the price at checkout is the price you pay. Everywhere else, the carrier will collect duties on delivery according to your local rules.",
        ],
      },
      {
        heading: "If something goes wrong",
        paragraphs: [
          "If tracking has not moved for five working days, write to studio@basic.studio with your order number and we will chase the carrier or send a replacement. You do not need to do the chasing.",
        ],
      },
    ],
  },
  {
    slug: "returns",
    title: "Returns & exchanges",
    summary: "Thirty days, free in most markets, no explanation needed.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: [
          "You have thirty days from delivery to return anything unworn, unwashed and with its tags attached. We do not ask why.",
        ],
      },
      {
        heading: "How to start one",
        list: [
          "Open the returns portal from the link in your dispatch email, or sign in to your account.",
          "Choose the items and whether you want a refund or an exchange.",
          "Print the prepaid label, or show the QR code at a drop-off point.",
          "Refunds are issued to the original payment method within five working days of the parcel arriving.",
        ],
      },
      {
        heading: "Return shipping",
        paragraphs: [
          "Returns are free from the EU, UK, US and Canada. From other markets a flat €15 is deducted from the refund to cover the label.",
          "Exchanges are always free, worldwide. If the size you want has sold out by the time your parcel reaches us, we refund instead and tell you when it is back.",
        ],
      },
      {
        heading: "Faulty items",
        paragraphs: [
          "A manufacturing fault is covered for two years from purchase, regardless of the thirty-day window. Send a photograph to studio@basic.studio and we will repair, replace or refund — your choice.",
        ],
      },
    ],
  },
  {
    slug: "size-guide",
    title: "Size guide",
    summary: "Body measurements, garment measurements, and how to choose between two sizes.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: [
          "Our sizing is based on body measurements, not garment measurements. Measure over your underwear, keep the tape level, and do not pull it tight.",
        ],
      },
      {
        heading: "Between two sizes?",
        paragraphs: [
          "For the rib series, take the smaller size — the fabric has six percent elastane and will settle. For the boxy tee, the denim jacket and the overcoat, take the larger size; they are cut square and are not meant to be close.",
        ],
      },
      {
        heading: "Still unsure",
        paragraphs: [
          "Write to studio@basic.studio with your usual size in a brand you know well and we will tell you honestly what to order. It is quicker than guessing and it saves both of us a return.",
        ],
      },
    ],
  },
  {
    slug: "care",
    title: "Garment care",
    summary: "How to keep cotton, merino, silk and leather looking like they did on day one.",
    updatedAt: "2026-09-01",
    sections: [
      {
        heading: "Cotton rib and jersey",
        list: [
          "Cold wash, gentle cycle, turned inside out.",
          "Dry flat in shade. Heat destroys elastane recovery permanently.",
          "Wash when it needs it, not on a schedule. Airing handles ordinary wear.",
        ],
      },
      {
        heading: "Merino and cashmere",
        list: [
          "Hand wash cool, or use a machine wool cycle with a wool detergent.",
          "Never wring. Press the water out, reshape, dry flat.",
          "Store folded. A hanger will pull the shoulders out within a season.",
          "De-pill by hand or with a comb — pilling is friction, not a defect.",
        ],
      },
      {
        heading: "Silk",
        list: [
          "Dry clean, or hand wash cool with a dedicated silk detergent.",
          "Dry flat away from direct light. Sun will fade sandwashed silk quickly.",
          "Iron on the reverse, cool, while slightly damp.",
        ],
      },
      {
        heading: "Leather and canvas",
        list: [
          "Wipe with a dry cloth. Never soak vegetable-tanned leather.",
          "Condition twice a year with a neutral cream.",
          "Expect the colour to deepen — that is the tannage, not wear.",
        ],
      },
    ],
  },
  {
    slug: "faq",
    title: "Frequently asked",
    summary: "Ordering, stock, payment, and the questions we actually get asked.",
    updatedAt: "2026-09-01",
    sections: [
      {
        heading: "When will my size be back in stock?",
        paragraphs: [
          "Core styles are restocked every four to six weeks. Add your email on the product page and you will be told the hour it lands — the list is first come, first served and we do not hold stock back for it.",
        ],
      },
      {
        heading: "Do you run sales?",
        paragraphs: [
          "No seasonal sales. We mark a style down only when it is being discontinued, and we say so on the page. The price you see is the price the garment costs to make properly plus a margin we can run a business on.",
        ],
      },
      {
        heading: "Can I change or cancel an order?",
        paragraphs: [
          "Yes, up until it is picked — usually a two-hour window. Email studio@basic.studio with your order number. After dispatch, use the returns process instead.",
        ],
      },
      {
        heading: "Which payment methods do you take?",
        paragraphs: [
          "Visa, Mastercard, American Express, iDEAL, Bancontact, Apple Pay, Google Pay, PayPal and Klarna. Card details never touch our servers.",
        ],
      },
      {
        heading: "Do you offer repairs?",
        paragraphs: [
          "We repair anything we have made, for as long as we are making it. Seams, hems and buttons are free. Larger repairs are quoted at cost with no margin.",
        ],
      },
      {
        heading: "Do you sell wholesale?",
        paragraphs: [
          "To a small number of stores whose buying we respect. Write to studio@basic.studio with a line sheet request and a link to your shop.",
        ],
      },
    ],
  },
];

export function getHelpDoc(slug: string) {
  return helpDocs.find((d) => d.slug === slug);
}

/** Garment measurements, in centimetres, laid flat. */
export const sizeChart = {
  columns: ["Size", "Chest", "Waist", "Hip", "Length", "Shoulder"],
  rows: [
    ["XS", "80 – 84", "62 – 66", "88 – 92", "54", "34"],
    ["S", "85 – 89", "67 – 71", "93 – 97", "56", "35.5"],
    ["M", "90 – 94", "72 – 76", "98 – 102", "58", "37"],
    ["L", "95 – 100", "77 – 82", "103 – 108", "60", "38.5"],
    ["XL", "101 – 107", "83 – 89", "109 – 115", "62", "40"],
  ],
};

/* ------------------------------------------------------------------- legal */

export const legalDocs: Doc[] = [
  {
    slug: "privacy",
    title: "Privacy",
    summary: "What we collect, why, and how to make us delete it.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: [
          "We collect the minimum needed to sell you a garment and get it to your door. We do not sell personal data, and we do not share it with advertising networks.",
        ],
      },
      {
        heading: "What we hold",
        list: [
          "Order data — name, delivery and billing address, email, phone, and what you bought.",
          "Account data — email and a hashed password, if you create an account.",
          "Payment data — held by our payment processor. We store only the last four digits and the card brand.",
          "Analytics — aggregate page views, with no cross-site tracking and no advertising identifiers.",
        ],
      },
      {
        heading: "How long we keep it",
        paragraphs: [
          "Order records are kept for seven years because tax law requires it. Everything else is deleted within twelve months of your last interaction, or immediately on request.",
        ],
      },
      {
        heading: "Your rights",
        paragraphs: [
          "Under the GDPR you can ask for a copy of everything we hold, ask us to correct it, or ask us to erase it. Write to studio@basic.studio and we will act within thirty days at the outside, usually within two.",
        ],
      },
    ],
  },
  {
    slug: "terms",
    title: "Terms of sale",
    summary: "The contract between you and Basic Studio B.V.",
    updatedAt: "2026-09-01",
    sections: [
      {
        heading: "The contract",
        paragraphs: [
          "A contract is formed when we send the dispatch confirmation, not when you place the order. If we cannot fulfil an order — a pricing error, or stock that sold twice — we will tell you and refund in full.",
        ],
      },
      {
        heading: "Pricing",
        paragraphs: [
          "Prices include VAT where applicable and are shown in euro. For the EU, UK, US and Canada, duties are prepaid and included. Elsewhere, duties are payable on receipt.",
        ],
      },
      {
        heading: "Right of withdrawal",
        paragraphs: [
          "EU and UK customers have a statutory fourteen-day right of withdrawal. Our thirty-day return policy is offered in addition to that right and does not replace it.",
        ],
      },
      {
        heading: "Liability",
        paragraphs: [
          "Nothing here limits liability for death, personal injury, or fraud. Otherwise our liability is limited to the value of the order.",
        ],
      },
      {
        heading: "Governing law",
        paragraphs: [
          "Dutch law governs these terms. Consumers keep the protection of the mandatory law of their country of residence.",
        ],
      },
    ],
  },
  {
    slug: "cookies",
    title: "Cookies",
    summary: "Three cookies, no advertising trackers.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: ["We set three cookies. None of them follow you off this site."],
      },
      {
        heading: "What they do",
        list: [
          "basic_session — keeps your bag and your sign-in for the length of the visit. Strictly necessary.",
          "basic_prefs — remembers your region and currency. Expires after twelve months.",
          "basic_stats — an anonymous, rotating identifier used to count visits. No cross-site profile is built.",
        ],
      },
      {
        heading: "Turning them off",
        paragraphs: [
          "Blocking basic_stats changes nothing about how the site works. Blocking basic_session will stop the bag from persisting between pages.",
        ],
      },
    ],
  },
  {
    slug: "accessibility",
    title: "Accessibility",
    summary: "Our commitment, the standard we hold, and how to report a barrier.",
    updatedAt: "2026-09-01",
    sections: [
      {
        paragraphs: [
          "We build against WCAG 2.2 Level AA and test with a keyboard and a screen reader before anything ships. This is a standard we hold ourselves to rather than a badge we bought.",
        ],
      },
      {
        heading: "What is in place",
        list: [
          "Every interactive element is reachable and operable by keyboard, with a visible focus ring.",
          "Colour contrast meets or exceeds 4.5:1 for body text and 3:1 for large text.",
          "Motion respects the prefers-reduced-motion setting — animation stops, content does not.",
          "Images carry descriptive alternative text; decorative images are hidden from assistive technology.",
        ],
      },
      {
        heading: "Reporting a barrier",
        paragraphs: [
          "If something on this site blocks you, write to studio@basic.studio. Tell us the page and what happened. We treat access bugs as release blockers, not backlog.",
        ],
      },
    ],
  },
];

export function getLegalDoc(slug: string) {
  return legalDocs.find((d) => d.slug === slug);
}

/* ----------------------------------------------------------------- careers */

export type Role = {
  slug: string;
  title: string;
  team: string;
  location: string;
  type: string;
  summary: string;
};

export const roles: Role[] = [
  {
    slug: "production-coordinator",
    title: "Production Coordinator",
    team: "Production",
    location: "Amsterdam",
    type: "Full time",
    summary:
      "Own the critical path between our mills in Portugal and Italy and the studio. You will spend a week a season on the factory floor.",
  },
  {
    slug: "pattern-cutter",
    title: "Pattern Cutter",
    team: "Design",
    location: "Amsterdam",
    type: "Full time",
    summary:
      "Grade and re-cut a short line properly rather than a long one quickly. Knitwear experience matters more than volume.",
  },
  {
    slug: "customer-experience",
    title: "Customer Experience Lead",
    team: "Studio",
    location: "Amsterdam / Remote",
    type: "Full time",
    summary:
      "Answer every email like a person who has held the garment. You will have the authority to fix things without asking.",
  },
  {
    slug: "retail-associate",
    title: "Retail Associate",
    team: "Retail",
    location: "Amsterdam — Keizersgracht",
    type: "Part time",
    summary:
      "Weekends and two weekdays in the flagship. No commission, no targets, no upselling.",
  },
];

/* ------------------------------------------------------------- brand story */

export const values = [
  {
    title: "A short line",
    body: "Eleven styles, restocked rather than replaced. We would rather re-cut something than add to the range.",
  },
  {
    title: "Named mills",
    body: "Every product page says where the cloth was made and where it was sewn. If we cannot name it, we do not sell it.",
  },
  {
    title: "Priced once",
    body: "No seasonal sales. A markdown only ever means a style is being discontinued, and the page says so.",
  },
  {
    title: "Repaired, not replaced",
    body: "Seams, hems and buttons repaired free for as long as we make the garment. Larger repairs quoted at cost.",
  },
];

export const timeline = [
  { year: "2023", text: "Two people, one tank, and a sample run of forty pieces that sold to friends." },
  { year: "2024", text: "First production run in Porto. The mock neck is re-cut twice before it ships." },
  { year: "2025", text: "Merino added from Biella. The line reaches eight styles and stops growing." },
  { year: "2026", text: "The Keizersgracht flagship opens. The Rib Series launches in four colourways." },
];

export const materials = [
  {
    name: "Long-staple organic cotton",
    origin: "Spun in Portugal",
    body: "34 mm staple and above, GOTS certified. Fewer joins in the yarn means a smoother surface and far less pilling.",
    image: "/textures/cloth-light.jpg",
  },
  {
    name: "Extra-fine merino",
    origin: "Spun in Biella, Italy",
    body: "18.5 micron, mulesing-free, traceable to the farm group. Fine enough to wear against the skin all day.",
    image: "/textures/cloth-warm.jpg",
  },
  {
    name: "Wool-cashmere melton",
    origin: "Milled in Yorkshire, England",
    body: "640 gsm, milled and finished in a mill that has run since 1837. Dense enough to hold a line without heavy interlining.",
    image: "/textures/cloth-dark.jpg",
  },
  {
    name: "Vegetable-tanned leather",
    origin: "Tanned in Tuscany, Italy",
    body: "Tanned with bark rather than chrome, in a consortium tannery that publishes its water treatment figures.",
    image: "/textures/rib-macro.jpg",
  },
];
