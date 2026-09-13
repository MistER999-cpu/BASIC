"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { legalNav, mainNav, site } from "@/lib/site";
import { cn } from "@/lib/cn";
import { useStore } from "@/components/providers/StoreProvider";
import { Overlay } from "@/components/ui/Overlay";
import { IconChevronDown } from "@/components/ui/icons";

export function MobileNav() {
  const { navOpen, setNavOpen } = useStore();
  const pathname = usePathname();
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => setNavOpen(false), [pathname, setNavOpen]);

  return (
    <Overlay
      open={navOpen}
      onClose={() => setNavOpen(false)}
      label="Menu"
      title="Menu"
      side="left"
      className="lg:hidden"
    >
      <nav aria-label="Mobile" className="flex-1 overflow-y-auto px-5 py-6">
        <ul className="flex flex-col">
          {mainNav.map((item) => {
            const open = expanded === item.label;
            return (
              <li key={item.label} className="border-b border-line">
                <div className="flex items-center justify-between">
                  <Link
                    href={item.href}
                    className="font-display flex-1 py-4 text-2xl leading-none"
                  >
                    {item.label}
                  </Link>
                  {item.groups && (
                    <button
                      type="button"
                      onClick={() => setExpanded(open ? null : item.label)}
                      aria-expanded={open}
                      className="flex h-11 w-11 items-center justify-center text-muted"
                    >
                      <IconChevronDown
                        className={cn(
                          "transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)]",
                          open && "rotate-180",
                        )}
                      />
                      <span className="sr-only">
                        {open ? "Collapse" : "Expand"} {item.label}
                      </span>
                    </button>
                  )}
                </div>
                {item.groups && open && (
                  <div className="flex flex-col gap-5 pb-5">
                    {item.groups.map((group) => (
                      <div key={group.heading} className="flex flex-col gap-2.5">
                        <p className="label text-faint">{group.heading}</p>
                        <ul className="flex flex-col gap-2.5">
                          {group.links.map((link) => (
                            <li key={link.href + link.label}>
                              <Link href={link.href} className="text-sm text-ink-soft">
                                {link.label}
                              </Link>
                            </li>
                          ))}
                        </ul>
                      </div>
                    ))}
                  </div>
                )}
              </li>
            );
          })}
        </ul>

        <ul className="mt-8 flex flex-col gap-3">
          {[
            { label: "Account", href: "/account" },
            { label: "Saved items", href: "/wishlist" },
            { label: "Help", href: "/help" },
            { label: "Stockists", href: "/stores" },
          ].map((link) => (
            <li key={link.href}>
              <Link href={link.href} className="label text-ink-soft">
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="shrink-0 border-t border-line px-5 py-5">
        <ul className="mb-4 flex flex-wrap gap-x-5 gap-y-2">
          {site.socials.map((s) => (
            <li key={s.label}>
              <a href={s.href} className="label text-muted" rel="noreferrer noopener" target="_blank">
                {s.label}
              </a>
            </li>
          ))}
        </ul>
        <ul className="flex flex-wrap gap-x-4 gap-y-2">
          {legalNav.map((l) => (
            <li key={l.href}>
              <Link href={l.href} className="label text-faint">
                {l.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </Overlay>
  );
}
