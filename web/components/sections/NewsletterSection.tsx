import Image from "next/image";
import { Container } from "@/components/ui/Container";
import { Eyebrow } from "@/components/ui/Eyebrow";
import { NewsletterForm } from "@/components/ui/NewsletterForm";
import { Reveal } from "@/components/ui/Reveal";

export function NewsletterSection() {
  return (
    <section className="relative overflow-hidden bg-ink text-paper">
      <Image
        src="/textures/cloth-dark.jpg"
        alt=""
        fill
        sizes="100vw"
        className="object-cover opacity-30"
      />
      <div className="relative">
        <Container className="py-24 sm:py-32">
          <Reveal className="mx-auto flex max-w-2xl flex-col items-center gap-7 text-center">
            <Eyebrow rule={false} className="text-paper/65">
              One letter a month
            </Eyebrow>
            <h2 className="font-display text-display font-normal">
              What we made, and what we got wrong
            </h2>
            <p className="text-lead text-paper/70">
              Restock notices, new colourways, and the occasional note from the factory floor.
              No offers — we do not run them.
            </p>
            <NewsletterForm tone="light" className="mt-2 max-w-md" />
            <p className="label text-paper/60">Unsubscribe in one click. We never share your address.</p>
          </Reveal>
        </Container>
      </div>
    </section>
  );
}
