import { Img as Image } from "@/components/ui/Img";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { Reveal } from "@/components/ui/Reveal";
import { cn } from "@/lib/cn";

type Props = {
  eyebrow: string;
  title: React.ReactNode;
  body: string[];
  image: string;
  imageAlt: string;
  cta?: { href: string; label: string };
  /** Puts the plate on the left instead of the right. */
  flip?: boolean;
  tone?: "paper" | "ink";
  aspect?: "portrait" | "landscape";
};

export function EditorialSplit({
  eyebrow,
  title,
  body,
  image,
  imageAlt,
  cta,
  flip = false,
  tone = "paper",
  aspect = "portrait",
}: Props) {
  const ink = tone === "ink";

  return (
    <section
      className={cn(
        "border-b py-20 sm:py-28",
        ink ? "border-paper/12 bg-ink text-paper" : "border-line",
      )}
    >
      <Container>
        <div className="grid items-center gap-12 lg:grid-cols-2 lg:gap-20">
          <Reveal className={cn(flip && "lg:order-2")}>
            <div
              className={cn(
                "relative overflow-hidden",
                ink ? "bg-ink-soft" : "bg-paper-deep",
                aspect === "portrait" ? "aspect-[4/5]" : "aspect-[3/2]",
              )}
            >
              <Image
                src={image}
                alt={imageAlt}
                fill
                sizes="(min-width: 1024px) 50vw, 100vw"
                className="object-cover"
              />
            </div>
          </Reveal>

          <Reveal delay={100} className={cn("flex flex-col gap-6", flip && "lg:order-1")}>
            <Eyebrow className={ink ? "text-paper/65" : undefined}>{eyebrow}</Eyebrow>
            <h2 className="font-display text-title font-normal">{title}</h2>
            <div className={cn("flex flex-col gap-4 text-lead", ink ? "text-paper/75" : "text-ink-soft")}>
              {body.map((paragraph) => (
                <p key={paragraph}>{paragraph}</p>
              ))}
            </div>
            {cta && (
              <ButtonLink
                href={cta.href}
                variant={ink ? "light" : "outline"}
                size="lg"
                className="mt-2 self-start"
              >
                {cta.label}
              </ButtonLink>
            )}
          </Reveal>
        </div>
      </Container>
    </section>
  );
}
