import { Img as Image } from "@/components/ui/Img";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { Reveal } from "@/components/ui/Reveal";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { getProduct } from "@/lib/products";

/** The signature product, shown as the full colourway range. */
export function FeaturedRange() {
  const product = getProduct("ribbed-mock-neck-tank");
  if (!product) return null;

  return (
    <section className="border-b border-line py-20 sm:py-28">
      <Container>
        <Reveal className="mx-auto flex max-w-3xl flex-col items-center gap-6 text-center">
          <Eyebrow rule={false}>The signature</Eyebrow>
          <h2 className="font-display text-display font-normal">{product.name}</h2>
          <p className="text-lead text-ink-soft">
            A fine 2×1 rib knitted to hold its shape at the neck. Four colourways, one gauge,
            and a mock collar that sits just high enough to read deliberate.
          </p>
        </Reveal>

        <Reveal delay={120} className="relative mt-14 overflow-hidden bg-paper-deep">
          <div className="relative aspect-[2/1] w-full">
            <Image
              src="/editorial/range.jpg"
              alt="Bone, Ink, Clay and Sand colourways of the Ribbed Mock-Neck Tank, side by side"
              fill
              sizes="100vw"
              className="object-cover"
            />
          </div>
        </Reveal>

        <Reveal delay={180} className="mt-10 flex flex-col items-center gap-8">
          <ul className="flex flex-wrap items-center justify-center gap-x-10 gap-y-4">
            {product.colourways.map((colour) => (
              <li key={colour.slug} className="flex items-center gap-2.5">
                <span
                  aria-hidden
                  className="h-3.5 w-3.5 rounded-full border border-line-strong"
                  style={{ backgroundColor: colour.hex }}
                />
                <span className="label text-ink-soft">{colour.name}</span>
              </li>
            ))}
          </ul>
          <ButtonLink href={`/shop/${product.slug}`} variant="outline" size="lg">
            View the tank
          </ButtonLink>
        </Reveal>
      </Container>
    </section>
  );
}
