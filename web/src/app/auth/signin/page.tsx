"use client";

import { useState } from "react";
import { requestMagicLink } from "@/lib/api";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError(null);
    try {
      await requestMagicLink(email);
      setStatus("sent");
    } catch (err) {
      setStatus("error");
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-6">
      <h1 className="mb-2 font-display text-3xl font-semibold text-ink">CreatorOS</h1>
      <p className="mb-8 font-body text-sm text-ink-muted">
        Sign in with your email — we&apos;ll send you a link, no password needed.
      </p>

      {status === "sent" ? (
        <p className="rounded-md border border-explore-teal/40 bg-surface p-4 font-body text-sm text-ink">
          Check your inbox for a sign-in link. It expires in 15 minutes.
        </p>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-3">
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            className="w-full rounded-md border border-surface-raised bg-surface px-3 py-2.5 font-body text-sm text-ink placeholder:text-ink-muted focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber"
          />
          <button
            type="submit"
            disabled={status === "sending"}
            className="w-full rounded-md bg-signal-amber px-4 py-2.5 font-display text-sm font-semibold text-canvas transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber disabled:opacity-50"
          >
            {status === "sending" ? "Sending…" : "Send sign-in link"}
          </button>
          {error && <p className="font-body text-sm text-alert-coral">{error}</p>}
        </form>
      )}
    </main>
  );
}
