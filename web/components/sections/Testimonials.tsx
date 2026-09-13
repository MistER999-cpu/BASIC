import { Container } from "@/components/ui/Container";
import { Reveal } from "@/components/ui/Reveal";
import { SectionHeading } from "@/components/ui/SectionHeading";
import { Rating } from "@/components/commerce/Rating";

const QUOTES = [
  {
    quote:
      "The neck still stands up after a year of weekly wear. I have never had a mock neck do that.",
    name: "Ines R.",
    detail: "The Ribbed Mock-Neck Tank, Ink",
    rating: 5,
  },
  {
    quote:
      "I ordered one to try and four more the following week. It is the only tank I reach for now.",
    name: "Marte K.",
    detail: "The Ribbed Mock-Neck Tank, Bone",
    rating: 5,
  },
  {
    quote:
      "Fine enough to wear under a shirt and warm enough to wear alone. Worth every euro.",
    name: "Daniel A.",
    detail: "The Merino Crew, Oat",
    rating: 5,
  },
  {
    quote:
      "Sized down on the advice in the size guide and it was exactly right. No return needed.",
    name: "Yuki T.",
    detail: "The Boxy Tee, Sage",
    rating: 4,
  },
];

export function Testimonials() {
  return (
    <section className="border-b border-line py-20 sm:py-28">
      <Container>
        <SectionHeading
          eyebrow="Wearers"
          title="What people say"
          link={{ href: "/shop", label: "Shop best sellers" }}
        />
        <ul className="mt-12 grid gap-x-8 gap-y-10 sm:grid-cols-2 lg:grid-cols-4">
          {QUOTES.map((item, i) => (
            <Reveal
              as="li"
              key={item.name}
              delay={i * 70}
              className="flex flex-col gap-4 border-t border-line pt-6"
            >
              <Rating value={item.rating} count={0} showCount={false} />
              <blockquote className="font-display text-lg leading-snug text-balance">
                “{item.quote}”
              </blockquote>
              <footer className="mt-auto">
                <p className="label">{item.name}</p>
                <p className="mt-1 text-[0.8125rem] text-muted">{item.detail}</p>
              </footer>
            </Reveal>
          ))}
        </ul>
      </Container>
    </section>
  );
}
