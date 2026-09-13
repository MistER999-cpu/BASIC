"use client";

import { Img as Image } from "@/components/ui/Img";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { mainNav } from "@/lib/site";
import { cn } from "@/lib/cn";
import { useStore } from "@/components/providers/StoreProvider";
import { IconBag, IconHeart, IconMenu, IconSearch, IconUser } from "@/components/ui/icons";
import { Wordmark } from "./Wordmark";

export function Header() {
  const pathname = usePathname();
  const { count, setCartOpen, setSearchOpen, setNavOpen, ready } = useStore();
  const [scrolled, setScrolled] = useState(false);
  const [openMenu, setOpenMenu] = useState<string | null>(null);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // Never leave a mega-menu hanging open across a navigation. Adjusting during
  // render rather than in an effect avoids a frame with the old menu still up.
  const [lastPath, setLastPath] = useState(pathname);
  if (pathname !== lastPath) {
    setLastPath(pathname);
    setOpenMenu(null);
  }

  const active = mainNav.find((item) => item.label === openMenu);

  return (
    <header
      className={cn(
        "sticky top-0 z-50 transition-[background-color,border-color,backdrop-filter]",
        "duration-[var(--duration-base)] ease-[var(--ease-out-quint)]",
        scrolled || openMenu
          ? "border-b border-line bg-paper/90 backdrop-blur-xl"
          : "border-b border-transparent bg-paper",
      )}
      onMouseLeave={() => setOpenMenu(null)}
    >
      <div className="mx-auto grid h-16 max-w-[130rem] grid-cols-[1fr_auto_1fr] items-center gap-4 px-5 sm:h-20 sm:px-8 lg:px-12">
        {/* Left — primary navigation */}
        <nav aria-label="Primary" className="hidden lg:block">
          <ul className="flex items-center gap-8">
            {mainNav.map((item) => {
              const isActive =
                pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
              return (
                <li key={item.label}>
                  <Link
                    href={item.href}
                    onMouseEnter={() => setOpenMenu(item.groups ? item.label : null)}
                    onFocus={() => setOpenMenu(item.groups ? item.label : null)}
                    aria-expanded={item.groups ? openMenu === item.label : undefined}
                    className={cn(
                      "label py-2 transition-colors duration-[var(--duration-quick)]",
                      isActive || openMenu === item.label ? "text-ink" : "text-ink-soft hover:text-ink",
                    )}
                  >
                    {item.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        </nav>

        {/* Mobile — menu trigger */}
        <div className="flex items-center lg:hidden">
          <button
            type="button"
            onClick={() => setNavOpen(true)}
            className="-ml-2 flex h-10 w-10 items-center justify-center text-ink"
          >
            <IconMenu />
            <span className="sr-only">Open menu</span>
          </button>
        </div>

        {/* Centre — wordmark */}
        <Wordmark className="justify-self-center" />

        {/* Right — utilities */}
        <div className="flex items-center justify-end gap-1 sm:gap-2">
          <button
            type="button"
            onClick={() => setSearchOpen(true)}
            className="flex h-10 w-10 items-center justify-center text-ink transition-opacity hover:opacity-60"
          >
            <IconSearch />
            <span className="sr-only">Search</span>
          </button>
          <Link
            href="/wishlist"
            className="hidden h-10 w-10 items-center justify-center text-ink transition-opacity hover:opacity-60 sm:flex"
          >
            <IconHeart />
            <span className="sr-only">Saved items</span>
          </Link>
          <Link
            href="/account"
            className="hidden h-10 w-10 items-center justify-center text-ink transition-opacity hover:opacity-60 sm:flex"
          >
            <IconUser />
            <span className="sr-only">Account</span>
          </Link>
          <button
            type="button"
            onClick={() => setCartOpen(true)}
            className="relative -mr-2 flex h-10 w-10 items-center justify-center text-ink transition-opacity hover:opacity-60"
          >
            <IconBag />
            <span className="sr-only">Bag</span>
            {ready && count > 0 && (
              <span className="absolute top-1.5 right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-ink px-1 text-[0.625rem] leading-none font-medium text-paper tabular-nums">
                {count}
              </span>
            )}
          </button>
        </div>
      </div>

      {/* Mega menu */}
      <div
        className={cn(
          "absolute inset-x-0 top-full hidden origin-top overflow-hidden border-b border-line bg-paper lg:block",
          "transition-[opacity,transform] duration-[var(--duration-base)] ease-[var(--ease-out-expo)]",
          active?.groups
            ? "pointer-events-auto translate-y-0 opacity-100"
            : "pointer-events-none -translate-y-2 opacity-0",
        )}
        aria-hidden={!active?.groups}
      >
        {active?.groups && (
          <div className="mx-auto grid max-w-[130rem] grid-cols-[repeat(3,minmax(0,14rem))_1fr] gap-12 px-12 py-12">
            {active.groups.map((group) => (
              <div key={group.heading} className="flex flex-col gap-5">
                <p className="label text-faint">{group.heading}</p>
                <ul className="flex flex-col gap-3">
                  {group.links.map((link) => (
                    <li key={link.href + link.label}>
                      <Link
                        href={link.href}
                        className="link-underline text-sm text-ink-soft hover:text-ink"
                      >
                        {link.label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}

            {active.feature && (
              <Link href={active.feature.href} className="group ml-auto flex w-full max-w-sm gap-5">
                <div className="relative aspect-[3/4] w-32 shrink-0 overflow-hidden bg-paper-deep">
                  <Image
                    src={active.feature.image}
                    alt=""
                    fill
                    sizes="128px"
                    className="object-cover transition-transform duration-[var(--duration-slow)] ease-[var(--ease-out-expo)] group-hover:scale-105"
                  />
                </div>
                <div className="flex flex-col gap-2 self-end pb-1">
                  <span className="label text-faint">{active.feature.eyebrow}</span>
                  <span className="font-display text-xl leading-tight">{active.feature.title}</span>
                  <span className="label link-underline self-start">Discover</span>
                </div>
              </Link>
            )}
          </div>
        )}
      </div>
    </header>
  );
}
