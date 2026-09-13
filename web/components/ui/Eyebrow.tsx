import { cn } from "@/lib/cn";

export function Eyebrow({
  children,
  className,
  rule = true,
}: {
  children: React.ReactNode;
  className?: string;
  rule?: boolean;
}) {
  return (
    <span className={cn("label inline-flex items-center gap-3 text-muted", className)}>
      {rule && <span aria-hidden className="h-px w-8 bg-current opacity-40" />}
      {children}
    </span>
  );
}
