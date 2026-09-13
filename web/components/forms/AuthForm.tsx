"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";

/**
 * Validation and state only — there is no auth backend in this build. Replace
 * the simulated submit with your session endpoint.
 */
export function AuthForm({ mode }: { mode: "login" | "register" }) {
  const [state, setState] = useState<"idle" | "sending" | "done">("idle");
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const next: Record<string, string> = {};
    if (mode === "register" && !String(data.get("name") ?? "").trim())
      next.name = "Please tell us your name.";
    if (!String(data.get("email") ?? "").includes("@")) next.email = "Enter a valid email address.";
    if (String(data.get("password") ?? "").length < 8)
      next.password = "Use at least eight characters.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setState("sending");
    await new Promise((r) => setTimeout(r, 700));
    setState("done");
  }

  if (state === "done") {
    return (
      <div className="border border-line p-8" role="status">
        <p className="font-display text-2xl">
          {mode === "login" ? "Check your inbox" : "Almost there"}
        </p>
        <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
          Authentication is not connected in this build. Wire{" "}
          <code className="text-ink">AuthForm</code> to your session endpoint to finish the flow.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-7">
      {mode === "register" && (
        <Field label="Name" name="name" autoComplete="name" error={errors.name} />
      )}
      <Field label="Email" name="email" type="email" autoComplete="email" error={errors.email} />
      <Field
        label="Password"
        name="password"
        type="password"
        autoComplete={mode === "login" ? "current-password" : "new-password"}
        error={errors.password}
      />

      {mode === "register" && (
        <label className="flex items-start gap-3 text-[0.8125rem] leading-relaxed text-muted">
          <input type="checkbox" name="newsletter" className="mt-0.5 accent-[var(--color-ink)]" />
          <span>Send me the monthly letter. Restocks and studio notes, no offers.</span>
        </label>
      )}

      <Button type="submit" disabled={state === "sending"} full size="lg">
        {state === "sending" ? "One moment" : mode === "login" ? "Sign in" : "Create account"}
      </Button>

      <p className="text-[0.8125rem] text-muted">
        {mode === "login" ? (
          <>
            No account yet?{" "}
            <Link href="/account/register" className="link-underline text-ink">
              Create one
            </Link>
          </>
        ) : (
          <>
            Already have an account?{" "}
            <Link href="/account/login" className="link-underline text-ink">
              Sign in
            </Link>
          </>
        )}
      </p>
    </form>
  );
}

function Field({
  label,
  name,
  type = "text",
  autoComplete,
  error,
}: {
  label: string;
  name: string;
  type?: string;
  autoComplete?: string;
  error?: string;
}) {
  return (
    <div className="flex flex-col gap-2">
      <label htmlFor={name} className="label text-muted">
        {label}
      </label>
      <input
        id={name}
        name={name}
        type={type}
        autoComplete={autoComplete}
        className="field"
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${name}-error` : undefined}
      />
      {error && (
        <p id={`${name}-error`} role="alert" className="label text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
