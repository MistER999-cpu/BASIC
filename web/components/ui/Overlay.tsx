"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/cn";
import { IconClose } from "./icons";

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),textarea:not([disabled]),[tabindex]:not([tabindex="-1"])';

type Props = {
  open: boolean;
  onClose: () => void;
  label: string;
  children: React.ReactNode;
  side?: "right" | "left" | "top";
  className?: string;
  /** Rendered in the panel header, beside the close button. */
  title?: React.ReactNode;
};

/**
 * Modal surface used for the bag, the mobile menu and search.
 *
 * Keeps focus inside while open and restores it to the trigger on close.
 * Escape and body-scroll locking are handled centrally in StoreProvider.
 */
export function Overlay({
  open,
  onClose,
  label,
  children,
  side = "right",
  className,
  title,
}: Props) {
  const panelRef = useRef<HTMLDivElement>(null);
  const returnTo = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (!open) return;
    returnTo.current = document.activeElement as HTMLElement;
    const panel = panelRef.current;
    const first = panel?.querySelector<HTMLElement>(FOCUSABLE);
    (first ?? panel)?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Tab" || !panel) return;
      const items = Array.from(panel.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
        (el) => el.offsetParent !== null,
      );
      if (items.length === 0) return;
      const firstEl = items[0];
      const lastEl = items[items.length - 1];
      if (e.shiftKey && document.activeElement === firstEl) {
        e.preventDefault();
        lastEl.focus();
      } else if (!e.shiftKey && document.activeElement === lastEl) {
        e.preventDefault();
        firstEl.focus();
      }
    };

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      returnTo.current?.focus?.();
    };
  }, [open]);

  const panelPosition = {
    right: cn("inset-y-0 right-0 h-full w-full max-w-[30rem]", open ? "translate-x-0" : "translate-x-full"),
    left: cn("inset-y-0 left-0 h-full w-full max-w-[26rem]", open ? "translate-x-0" : "-translate-x-full"),
    top: cn("inset-x-0 top-0 w-full", open ? "translate-y-0" : "-translate-y-full"),
  }[side];

  return (
    <div
      className={cn("fixed inset-0 z-[100]", open ? "visible" : "invisible")}
      aria-hidden={!open}
    >
      <div
        onClick={onClose}
        className={cn(
          "absolute inset-0 bg-ink/25 backdrop-blur-[2px] transition-opacity duration-[var(--duration-base)]",
          open ? "opacity-100" : "opacity-0",
        )}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
        className={cn(
          "absolute flex flex-col bg-paper shadow-[0_0_60px_rgba(22,17,14,0.10)] outline-none",
          "transition-transform duration-[var(--duration-base)] ease-[var(--ease-out-expo)]",
          panelPosition,
          className,
        )}
      >
        <div className="flex h-16 shrink-0 items-center justify-between gap-4 border-b border-line px-5 sm:px-7">
          <div className="label min-w-0 truncate">{title ?? label}</div>
          <button
            type="button"
            onClick={onClose}
            className="-mr-2 flex h-10 w-10 shrink-0 items-center justify-center text-ink transition-opacity hover:opacity-60"
          >
            <IconClose />
            <span className="sr-only">Close</span>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
