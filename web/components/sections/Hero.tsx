import { Img as Image } from "@/components/ui/Img";
import Link from "next/link";
import { Container } from "@/components/ui/Container";
import { ButtonLink } from "@/components/ui/Button";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { IconArrowRight } from "@/components/ui/icons";

/**
 * Editorial split: type carries the left column, a single full-bleed plate the
 * right. Entrance is a staggered CSS animation rather than JS, so it runs on
 * first paint and costs nothing.
 */
export function Hero() {
  return (
    <section className="relative overflow-hidden border-b border-line">
      <Container className="relative">
        <div className="grid items-end gap-10 pt-14 pb-16 sm:pt-20 lg:grid-cols-12 lg:gap-8 lg:pt-24 lg:pb-24">
          <div className="flex flex-col gap-8 lg:col-span-7 lg:pb-6">
            <div style={{ animationDelay: "60ms" }} className="animate-[var(--animate-rise)]">
              <Eyebrow>Autumn 2026 — The Rib Series</Eyebrow>
            </div>

            <h1
              style={{ animationDelay: "140ms" }}
              className="animate-[var(--animate-rise)] font-display text-hero font-normal"
            >
              The essentials,
              <br />
              <span className="italic">considered.</span>
            </h1>

            <p
              style={{ animationDelay: "260ms" }}
              className="animate-[var(--animate-rise)] max-w-lg text-lead text-ink-soft"
            >
              Eleven styles, cut from long-staple cotton and extra-fine merino, made in
              limited runs in Portugal and Italy. Restocked rather than replaced.
            </p>

            <div
              style={{ animationDelay: "360ms" }}
              className="animate-[var(--animate-rise)] flex flex-wrap items-center gap-4"
            >
              <ButtonLink href="/shop" size="lg">
                Shop the collection
              </ButtonLink>
              <Link
                href="/collections/rib-series"
                className="label link-underline inline-flex items-center gap-2 px-2 py-3"
              >
                The Rib Series
                <IconArrowRight />
              </Link>
            </div>

            <dl
              style={{ animationDelay: "460ms" }}
              className="animate-[var(--animate-rise)] mt-4 grid max-w-lg grid-cols-3 gap-6 border-t border-line pt-6"
            >
              {[
                ["11", "styles in the line"],
                ["4", "named mills"],
                ["30", "day returns"],
              ].map(([value, label]) => (
                <div key={label} className="flex flex-col gap-1">
                  <dt className="font-display text-2xl leading-none">{value}</dt>
                  <dd className="label text-muted">{label}</dd>
                </div>
              ))}
            </dl>
          </div>

          <div
            style={{ animationDelay: "200ms" }}
            className="animate-[var(--animate-rise)] relative lg:col-span-5"
          >
            <div className="relative aspect-[4/5] w-full overflow-hidden bg-paper-deep lg:aspect-[3/4]">
              <Image
                src="/editorial/hero.jpg"
                alt="The Ribbed Mock-Neck Tank in Clay, photographed flat against paper"
                fill
                priority
                sizes="(min-width: 1024px) 40vw, 100vw"
                className="object-cover"
              />
            </div>
            <figcaption className="label mt-4 flex items-center justify-between text-muted">
              <span>The Ribbed Mock-Neck Tank</span>
              <Link href="/shop/ribbed-mock-neck-tank" className="link-underline text-ink">
                €68
              </Link>
            </figcaption>
          </div>
        </div>
      </Container>
    </section>
  );
}
