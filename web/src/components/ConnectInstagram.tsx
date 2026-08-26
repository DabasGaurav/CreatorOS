import { instagramAuthorizeUrl } from "@/lib/api";

export default function ConnectInstagram({
  sessionToken,
  error,
}: {
  sessionToken: string;
  error: string | null;
}) {
  return (
    <div className="mx-auto max-w-sm space-y-4 text-center">
      <div
        className="mx-auto aspect-[9/16] w-full rounded-lg border-2 border-dashed border-surface-raised"
        aria-hidden="true"
      />
      <p className="font-body text-sm text-ink-muted">
        Connect your Instagram Business or Creator account to build your Creator DNA and start
        getting recommendations.
      </p>
      {error && (
        <p className="rounded-md border border-alert-coral/40 bg-surface p-3 font-body text-xs text-alert-coral">
          {error === "connect_failed"
            ? "Couldn't connect that account — make sure it's a Business/Creator account and that you've been added as a Tester on the app, then try again."
            : error}
        </p>
      )}
      <a
        href={instagramAuthorizeUrl(sessionToken)}
        className="inline-block rounded-md bg-signal-amber px-6 py-3 font-display text-base font-semibold text-canvas transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber"
      >
        Connect Instagram
      </a>
    </div>
  );
}
