type IconProps = React.SVGProps<SVGSVGElement>;

const base = {
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.25,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
  "aria-hidden": true,
  focusable: false,
};

export const IconSearch = (p: IconProps) => (
  <svg {...base} width="18" height="18" {...p}>
    <circle cx="11" cy="11" r="6.5" />
    <path d="m16 16 4.5 4.5" />
  </svg>
);

export const IconBag = (p: IconProps) => (
  <svg {...base} width="18" height="18" {...p}>
    <path d="M4.5 7.5h15l-1 12.5h-13z" />
    <path d="M8.75 10V6.75a3.25 3.25 0 0 1 6.5 0V10" />
  </svg>
);

export const IconUser = (p: IconProps) => (
  <svg {...base} width="18" height="18" {...p}>
    <circle cx="12" cy="8.5" r="3.75" />
    <path d="M4.75 20c.9-3.9 3.8-5.9 7.25-5.9s6.35 2 7.25 5.9" />
  </svg>
);

export const IconHeart = (p: IconProps) => (
  <svg {...base} width="18" height="18" {...p}>
    <path d="M12 20s-7.5-4.4-7.5-9.2A4.3 4.3 0 0 1 12 8.2a4.3 4.3 0 0 1 7.5 2.6C19.5 15.6 12 20 12 20Z" />
  </svg>
);

export const IconClose = (p: IconProps) => (
  <svg {...base} width="18" height="18" {...p}>
    <path d="m6 6 12 12M18 6 6 18" />
  </svg>
);

export const IconMenu = (p: IconProps) => (
  <svg {...base} width="20" height="20" {...p}>
    <path d="M3.5 8h17M3.5 16h17" />
  </svg>
);

export const IconArrowRight = (p: IconProps) => (
  <svg {...base} width="16" height="16" {...p}>
    <path d="M4 12h15.5M13.5 6l6 6-6 6" />
  </svg>
);

export const IconArrowLeft = (p: IconProps) => (
  <svg {...base} width="16" height="16" {...p}>
    <path d="M20 12H4.5M10.5 6l-6 6 6 6" />
  </svg>
);

export const IconChevronDown = (p: IconProps) => (
  <svg {...base} width="14" height="14" {...p}>
    <path d="m5 9 7 7 7-7" />
  </svg>
);

export const IconMinus = (p: IconProps) => (
  <svg {...base} width="14" height="14" {...p}>
    <path d="M5 12h14" />
  </svg>
);

export const IconPlus = (p: IconProps) => (
  <svg {...base} width="14" height="14" {...p}>
    <path d="M12 5v14M5 12h14" />
  </svg>
);

export const IconCheck = (p: IconProps) => (
  <svg {...base} width="14" height="14" {...p}>
    <path d="m4.5 12.5 5 5 10-11" />
  </svg>
);

export const IconStar = (p: IconProps) => (
  <svg viewBox="0 0 24 24" width="13" height="13" fill="currentColor" aria-hidden focusable="false" {...p}>
    <path d="m12 3 2.6 5.9 6.4.6-4.8 4.3 1.4 6.3L12 16.8 6.4 20.1l1.4-6.3L3 9.5l6.4-.6z" />
  </svg>
);
