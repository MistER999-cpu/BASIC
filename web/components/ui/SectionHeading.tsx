import Link from "next/link";
import { cn } from "@/lib/cn";
import { Eyebrow } from "./Eyebrow";

type Props = {
  eyebrow?: string;
  title: React.ReactNode;
  lede?: string;
  link?: { href: string; label: string };
  align?: "left" | "center";
  className?: string;
  as?: "h1" | "h2" | "h3";
};

export function SectionHeading({
  eyebrow,
  title,
  lede,
  link,
  align = "left",
  className,
  as: Tag = "h2",
}: Props) {
  return (
    <div
      className={cn(
        "flex flex-col gap-6",
        align === "center" ? "items-center text-center" : "items-start",
        link && align === "left" && "md:flex-row md:items-end md:justify-between md:gap-12",
        className,
      )}
    >
      <div className={cn("flex flex-col gap-4", align === "center" && "items-center")}>
        {eyebrow && <Eyebrow rule={align === "left"}>{eyebrow}</Eyebrow>}
        <Tag className="font-display text-title font-normal">{title}</Tag>
        {lede && (
          <p className={cn("text-lead text-ink-soft", align === "center" ? "max-w-2xl" : "max-w-xl")}>
            {lede}
          </p>
        )}
      </div>
      {link && (
        <Link href={link.href} className="label link-underline shrink-0 text-ink">
          {link.label}
        </Link>
      )}
    </div>
  );
}
