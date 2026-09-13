"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { cn } from "@/lib/cn";
import { IconArrowRight, IconSearch } from "@/components/ui/icons";

export function SearchField({
  initialQuery = "",
  className,
}: {
  initialQuery?: string;
  className?: string;
}) {
  const [value, setValue] = useState(initialQuery);
  const router = useRouter();

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const q = value.trim();
        router.push(q ? `/search?q=${encodeURIComponent(q)}` : "/search");
      }}
      className={cn("w-full", className)}
    >
      <label htmlFor="search-page" className="sr-only">
        Search products
      </label>
      <div className="flex items-center gap-3 border-b border-line-strong focus-within:border-ink">
        <IconSearch className="shrink-0 text-muted" />
        <input
          id="search-page"
          type="search"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Style, colour or fabric"
          className="w-full bg-transparent py-3 outline-none placeholder:text-faint"
        />
        <button type="submit" className="label flex shrink-0 items-center gap-2 py-3 hover:opacity-60">
          Search
          <IconArrowRight />
        </button>
      </div>
    </form>
  );
}
