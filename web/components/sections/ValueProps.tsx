import { Container } from "@/components/ui/Container";
import { Reveal } from "@/components/ui/Reveal";
import { values } from "@/lib/content";

export function ValueProps() {
  return (
    <section className="border-b border-line py-16 sm:py-20">
      <Container>
        <ul className="grid gap-10 sm:grid-cols-2 lg:grid-cols-4 lg:gap-12">
          {values.map((value, i) => (
            <Reveal as="li" key={value.title} delay={i * 70} className="flex flex-col gap-3">
              <span aria-hidden className="label text-faint tabular-nums">
                {String(i + 1).padStart(2, "0")}
              </span>
              <h3 className="font-display text-xl leading-tight">{value.title}</h3>
              <p className="text-sm leading-relaxed text-muted">{value.body}</p>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
