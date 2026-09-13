import { Container } from "@/components/ui/Container";
import { Breadcrumbs, type Crumb } from "@/components/ui/Breadcrumbs";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { cn } from "@/lib/cn";

export function PageHeader({
  eyebrow,
  title,
  lede,
  crumbs,
  align = "left",
  className,
  children,
}: {
  eyebrow?: string;
  title: React.ReactNode;
  lede?: string;
  crumbs?: Crumb[];
  align?: "left" | "center";
  className?: string;
  children?: React.ReactNode;
}) {
  return (
    <section className={cn("border-b border-line", className)}>
      <Container className="pt-8 pb-12 sm:pt-10 sm:pb-16">
        {crumbs && <Breadcrumbs items={crumbs} />}
        <div
          className={cn(
            "flex flex-col gap-5",
            crumbs && "mt-8",
            align === "center" && "mx-auto max-w-3xl items-center text-center",
          )}
        >
          {eyebrow && <Eyebrow rule={align === "left"}>{eyebrow}</Eyebrow>}
          <h1 className="font-display text-display font-normal">{title}</h1>
          {lede && (
            <p className={cn("text-lead text-ink-soft", align === "left" ? "max-w-2xl" : "max-w-2xl")}>
              {lede}
            </p>
          )}
          {children}
        </div>
      </Container>
    </section>
  );
}
