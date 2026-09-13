"use client";

import { useState } from "react";
import { cn } from "@/lib/cn";
import { IconArrowRight } from "./icons";

/**
 * Front-end only for now — wire `onSubmit` to the ESP of your choice.
 * State machine is deliberate so the eventual network call has somewhere to go.
 */
export function NewsletterForm({
  className,
  tone = "dark",
  label = "Email address",
}: {
  className?: string;
  tone?: "dark" | "light";
  label?: string;
}) {
  const [email, setEmail] = useState("");
  const [state, setState] = useState<"idle" | "loading" | "done" | "error">("idle");

  const light = tone === "light";

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!email.includes("@")) {
      setState("error");
      return;
    }
    setState("loading");
    // Replace with a POST to your list provider.
    await new Promise((r) => setTimeout(r, 600));
    setState("done");
    setEmail("");
  }

  if (state === "done") {
    return (
      <p className={cn("label", light ? "text-paper" : "text-ink", className)} role="status">
        Thank you — please confirm via the email we just sent.
      </p>
    );
  }

  return (
    <form onSubmit={onSubmit} className={cn("w-full", className)} noValidate>
      <div
        className={cn(
          "flex items-center gap-3 border-b transition-colors",
          light ? "border-paper/35 focus-within:border-paper" : "border-line-strong focus-within:border-ink",
        )}
      >
        <label htmlFor="newsletter-email" className="sr-only">
          {label}
        </label>
        <input
          id="newsletter-email"
          type="email"
          name="email"
          autoComplete="email"
          required
          placeholder={label}
          value={email}
          onChange={(e) => {
            setEmail(e.target.value);
            if (state === "error") setState("idle");
          }}
          aria-invalid={state === "error"}
          className={cn(
            "w-full bg-transparent py-3 text-sm outline-none",
            light ? "text-paper placeholder:text-paper/60" : "text-ink placeholder:text-faint",
          )}
        />
        <button
          type="submit"
          disabled={state === "loading"}
          className={cn(
            "label flex shrink-0 items-center gap-2 py-3 transition-opacity disabled:opacity-40",
            light ? "text-paper hover:opacity-70" : "text-ink hover:opacity-60",
          )}
        >
          {state === "loading" ? "Sending" : "Sign up"}
          <IconArrowRight />
        </button>
      </div>
      {state === "error" && (
        <p role="alert" className="label mt-3 text-danger">
          Please enter a valid email address.
        </p>
      )}
    </form>
  );
}
