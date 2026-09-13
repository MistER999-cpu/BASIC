import Link from "next/link";
import { cn } from "@/lib/cn";

type Variant = "solid" | "outline" | "ghost" | "light";
type Size = "sm" | "md" | "lg";

const base =
  "inline-flex items-center justify-center gap-2.5 label whitespace-nowrap select-none " +
  "transition-[background-color,color,border-color,opacity] duration-[var(--duration-quick)] " +
  "ease-[var(--ease-out-quint)] disabled:opacity-40 disabled:pointer-events-none";

const variants: Record<Variant, string> = {
  solid: "bg-ink text-paper hover:bg-ink-soft",
  outline: "border border-ink text-ink hover:bg-ink hover:text-paper",
  ghost: "text-ink hover:text-muted",
  light: "bg-paper text-ink hover:bg-bone",
};

const sizes: Record<Size, string> = {
  sm: "h-9 px-4",
  md: "h-12 px-7",
  lg: "h-14 px-9",
};

type CommonProps = {
  variant?: Variant;
  size?: Size;
  className?: string;
  children: React.ReactNode;
  full?: boolean;
};

export function Button({
  variant = "solid",
  size = "md",
  className,
  full,
  children,
  ...rest
}: CommonProps & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={cn(base, variants[variant], sizes[size], full && "w-full", className)}
      {...rest}
    >
      {children}
    </button>
  );
}

export function ButtonLink({
  variant = "solid",
  size = "md",
  className,
  full,
  children,
  href,
  ...rest
}: CommonProps & { href: string } & Omit<React.ComponentProps<typeof Link>, "href" | "children">) {
  return (
    <Link
      href={href}
      className={cn(base, variants[variant], sizes[size], full && "w-full", className)}
      {...rest}
    >
      {children}
    </Link>
  );
}
