"use client";

import { useStore } from "@/components/providers/StoreProvider";
import { IconHeart } from "@/components/ui/icons";
import { cn } from "@/lib/cn";

export function SaveButton({
  slug,
  name,
  className,
  withLabel = false,
}: {
  slug: string;
  name: string;
  className?: string;
  withLabel?: boolean;
}) {
  const { isSaved, toggleWishlist, ready } = useStore();
  const saved = ready && isSaved(slug);

  return (
    <button
      type="button"
      onClick={() => toggleWishlist(slug)}
      aria-pressed={saved}
      className={cn(
        "inline-flex items-center gap-2 transition-colors duration-[var(--duration-quick)]",
        saved ? "text-ink" : "text-muted hover:text-ink",
        className,
      )}
    >
      <IconHeart className={saved ? "fill-current" : undefined} />
      {withLabel && <span className="label">{saved ? "Saved" : "Save"}</span>}
      <span className="sr-only">
        {saved ? `Remove ${name} from saved items` : `Save ${name}`}
      </span>
    </button>
  );
}
