import { Container } from "@/components/ui/Container";
import { Reveal } from "@/components/ui/Reveal";

const PRESS = [
  { name: "Monocle", quote: "A masterclass in restraint." },
  { name: "The Gentlewoman", quote: "Eleven things, all of them right." },
  { name: "Kinfolk", quote: "Quietly, obsessively made." },
  { name: "Cereal", quote: "The neck alone is worth it." },
];

export function PressStrip() {
  return (
    <section className="border-b border-line bg-paper-deep py-14">
      <Container>
        <ul className="grid gap-8 sm:grid-cols-2 lg:grid-cols-4">
          {PRESS.map((item, i) => (
            <Reveal as="li" key={item.name} delay={i * 60} className="flex flex-col gap-2">
              <p className="font-display text-lg leading-snug text-balance">“{item.quote}”</p>
              <p className="label text-muted">{item.name}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
