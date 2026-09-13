import { cn } from "@/lib/cn";

type Props = {
  children: React.ReactNode;
  className?: string;
  size?: "default" | "wide" | "narrow" | "full";
  as?: "div" | "section" | "header" | "footer" | "article" | "nav" | "main";
};

const sizes = {
  narrow: "max-w-3xl",
  default: "max-w-[110rem]",
  wide: "max-w-[130rem]",
  full: "max-w-none",
};

export function Container({ children, className, size = "default", as: Tag = "div" }: Props) {
  return (
    <Tag className={cn("mx-auto w-full px-5 sm:px-8 lg:px-12", sizes[size], className)}>
      {children}
    </Tag>
  );
}
