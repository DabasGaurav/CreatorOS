"use client";

import { Suspense, useCallback, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { createRecommendation, getCreator, getRecommendation } from "@/lib/api";
import { clearSession, getSession } from "@/lib/session";
import type { Creator, CreatorDNA, Recommendation } from "@/lib/types";
import ConnectInstagram from "@/components/ConnectInstagram";
import CreatorDNASummary from "@/components/CreatorDNASummary";
import EmptyState from "@/components/EmptyState";
import LoadingState from "@/components/LoadingState";
import RecommendationCard from "@/components/RecommendationCard";

const POLL_INTERVAL_MS = 2000;

function CoreScreen() {
  const router = useRouter();
  const searchParams = useSearchParams();
  // ?creator=<uuid> stays as a dev-only override (useful for local testing
  // without a mailbox handy); a signed-in session is the real path. Read
  // once via a lazy initializer rather than an effect+setState — by the time
  // this client component mounts (it's under Suspense from useSearchParams),
  // window/localStorage are already available, so there's no async gap to
  // bridge with an effect.
  const [session] = useState(() => getSession());
  const [creatorId] = useState<string | null>(
    () => searchParams.get("creator") ?? session?.creator_id ?? null,
  );
  const instagramError = searchParams.get("instagram_error");
  const justConnected = searchParams.get("connected") === "1";

  const [creator, setCreator] = useState<Creator | null>(null);
  const [dna, setDna] = useState<CreatorDNA | null>(null);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!creatorId) return;
    getCreator(creatorId)
      .then((c) => {
        setCreator(c);
        setDna(c.dna);
      })
      .catch((e) => setLoadError(e instanceof Error ? e.message : "Failed to load creator"));
  }, [creatorId]);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  useEffect(() => stopPolling, [stopPolling]);

  const handleGenerate = useCallback(async () => {
    if (!creatorId) return;
    setError(null);
    try {
      const { request_id } = await createRecommendation(creatorId);
      const initial = await getRecommendation(request_id);
      setRecommendation(initial);

      pollTimer.current = setInterval(async () => {
        try {
          const updated = await getRecommendation(request_id);
          setRecommendation(updated);
          if (updated.status === "completed" || updated.status === "failed") {
            stopPolling();
          }
        } catch (e) {
          stopPolling();
          setError(e instanceof Error ? e.message : "Failed to poll recommendation");
        }
      }, POLL_INTERVAL_MS);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start recommendation");
    }
  }, [creatorId, stopPolling]);

  if (!creatorId) {
    return (
      <main className="mx-auto flex min-h-screen max-w-sm flex-col items-center justify-center px-6 text-center">
        <p className="mb-4 font-body text-sm text-ink-muted">You&apos;re not signed in.</p>
        <a
          href="/auth/signin"
          className="rounded-md bg-signal-amber px-4 py-2 font-display text-sm font-semibold text-canvas"
        >
          Sign in
        </a>
      </main>
    );
  }

  if (loadError) {
    return (
      <main className="mx-auto flex min-h-screen max-w-md flex-col items-center justify-center px-6 text-center">
        <p className="font-body text-sm text-alert-coral">{loadError}</p>
      </main>
    );
  }

  const isBusy = recommendation?.status === "pending" || recommendation?.status === "running";
  const isDone = recommendation?.status === "completed";
  const isFailed = recommendation?.status === "failed";

  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-4 py-8 sm:px-6">
      <div className="mb-8 flex items-start justify-between gap-4">
        <h1 className="font-display text-3xl font-semibold text-ink sm:text-4xl">CreatorSignal.ai</h1>
        <button
          type="button"
          onClick={() => {
            clearSession();
            router.push("/auth/signin");
          }}
          className="font-body text-xs text-ink-muted underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber"
        >
          Sign out
        </button>
      </div>

      {creator && !creator.instagram_connected ? (
        <>
          {session && (
            <ConnectInstagram sessionToken={session.session_token} error={instagramError} />
          )}
        </>
      ) : (
        <>
          <div className="mb-8">{creator && <CreatorDNASummary creator={creator} dna={dna} />}</div>

          {justConnected && !recommendation && (
            <p className="mb-4 font-body text-sm text-explore-teal">
              Instagram connected — building your Creator DNA in the background. This can take a
              minute; refresh if it&apos;s not showing yet.
            </p>
          )}

          {error && <p className="mb-4 font-body text-sm text-alert-coral">{error}</p>}

          {!recommendation && <EmptyState onGenerate={handleGenerate} disabled={!creator} />}

          {isBusy && <LoadingState stage={recommendation?.current_stage ?? null} />}

          {isFailed && (
            <div className="mx-auto max-w-sm space-y-4 text-center">
              <p className="font-body text-sm text-alert-coral">
                Something went wrong: {recommendation?.error ?? "unknown error"}
              </p>
              <button
                type="button"
                onClick={() => setRecommendation(null)}
                className="rounded-md bg-surface-raised px-4 py-2 font-body text-sm text-ink"
              >
                Try again
              </button>
            </div>
          )}

          {isDone && recommendation && <RecommendationCard recommendation={recommendation} />}
        </>
      )}
    </main>
  );
}

export default function Home() {
  return (
    <Suspense>
      <CoreScreen />
    </Suspense>
  );
}
