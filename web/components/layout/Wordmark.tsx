import Link from "next/link";
import { cn } from "@/lib/cn";

export function Wordmark({
  className,
  size = "md",
}: {
  className?: string;
  size?: "sm" | "md" | "lg";
}) {
  const sizes = {
    sm: "text-base",
    md: "text-lg sm:text-xl",
    lg: "text-2xl",
  };
  return (
    <Link
      href="/"
      className={cn(
        "font-medium tracking-[var(--tracking-wordmark)] uppercase",
        sizes[size],
        className,
      )}
    >
      Basic
      <span className="sr-only"> — home</span>
    </Link>
  );
}
