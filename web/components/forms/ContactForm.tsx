"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/cn";

const SUBJECTS = ["An order", "Sizing advice", "A repair", "Wholesale or press", "Something else"];

/**
 * Client-side validation and state only — point `onSubmit` at your inbox or
 * helpdesk when the backend exists.
 */
export function ContactForm({ className }: { className?: string }) {
  const [state, setState] = useState<"idle" | "sending" | "sent">("idle");
  const [errors, setErrors] = useState<Record<string, string>>({});

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const next: Record<string, string> = {};
    if (!String(data.get("name") ?? "").trim()) next.name = "Please tell us your name.";
    if (!String(data.get("email") ?? "").includes("@")) next.email = "Please enter a valid email address.";
    if (String(data.get("message") ?? "").trim().length < 10)
      next.message = "A little more detail will help us answer properly.";
    setErrors(next);
    if (Object.keys(next).length) return;

    setState("sending");
    await new Promise((r) => setTimeout(r, 700));
    setState("sent");
  }

  if (state === "sent") {
    return (
      <div className={cn("border border-line p-8", className)} role="status">
        <p className="font-display text-2xl">Message received</p>
        <p className="mt-3 text-[0.9375rem] leading-relaxed text-ink-soft">
          We answer within one working day, usually sooner. If it is urgent, call the studio on
          weekdays between 09:00 and 17:30 CET.
        </p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className={cn("flex flex-col gap-7", className)}>
      <Field label="Name" name="name" autoComplete="name" error={errors.name} />
      <Field label="Email" name="email" type="email" autoComplete="email" error={errors.email} />
      <Field label="Order number (optional)" name="order" autoComplete="off" />

      <div className="flex flex-col gap-2">
        <label htmlFor="subject" className="label text-muted">
          Subject
        </label>
        <select id="subject" name="subject" className="field cursor-pointer">
          {SUBJECTS.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <label htmlFor="message" className="label text-muted">
          Message
        </label>
        <textarea
          id="message"
          name="message"
          rows={5}
          className="field resize-y"
          aria-invalid={Boolean(errors.message)}
          aria-describedby={errors.message ? "message-error" : undefined}
        />
        {errors.message && (
          <p id="message-error" role="alert" className="label text-danger">
            {errors.message}
          </p>
        )}
      </div>

      <Button type="submit" disabled={state === "sending"} full size="lg">
        {state === "sending" ? "Sending" : "Send message"}
      </Button>

      <p className="text-[0.8125rem] leading-relaxed text-muted">
        We use your message only to answer it. Read the{" "}
        <Link href="/legal/privacy" className="link-underline text-ink">
          privacy notice
        </Link>
        .
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
