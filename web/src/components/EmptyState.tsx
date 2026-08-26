export default function EmptyState({
  onGenerate,
  disabled,
}: {
  onGenerate: () => void;
  disabled?: boolean;
}) {
  return (
    <div className="mx-auto flex max-w-xs flex-col items-center gap-6">
      <div
        className="aspect-[9/16] w-full rounded-lg border-2 border-dashed border-surface-raised"
        aria-hidden="true"
      />
      <div className="text-center">
        <p className="font-body text-sm text-ink-muted">
          No active recommendation. Generate one on demand — evidence included.
        </p>
      </div>
      <button
        type="button"
        onClick={onGenerate}
        disabled={disabled}
        className="rounded-md bg-signal-amber px-6 py-3 font-display text-base font-semibold text-canvas transition-opacity hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal-amber disabled:opacity-50"
      >
        Generate Recommendation
      </button>
    </div>
  );
}
