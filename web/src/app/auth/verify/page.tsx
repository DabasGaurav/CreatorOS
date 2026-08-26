"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { verifyMagicLink } from "@/lib/api";
import { saveSession } from "@/lib/session";

function VerifyInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [asyncError, setAsyncError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) return; // "missing token" is handled as a derived render below
    verifyMagicLink(token)
      .then(({ session_token, creator_id }) => {
        saveSession({ session_token, creator_id });
        router.replace("/");
      })
      .catch((err) => {
        setAsyncError(
          err instanceof Error ? err.message : "That link is invalid, expired, or already used.",
        );
      });
  }, [token, router]);

  const error = token ? asyncError : "Missing sign-in token.";

  return (
    <main className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center px-6 text-center">
      {error ? (
        <>
          <p className="mb-4 font-body text-sm text-alert-coral">{error}</p>
          <a href="/auth/signin" className="font-body text-sm text-signal-amber underline">
            Request a new link
          </a>
        </>
      ) : (
        <p className="font-body text-sm text-ink-muted">Signing you in…</p>
      )}
    </main>
  );
}

export default function VerifyPage() {
  return (
    <Suspense>
      <VerifyInner />
    </Suspense>
  );
}
