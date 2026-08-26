export default function ScoreBadge({
  score,
  selectionType,
}: {
  score: number | null;
  selectionType: "exploit" | "explore" | null;
}) {
  const isExplore = selectionType === "explore";
  return (
    <div
      className={`absolute top-3 right-3 rounded-md px-2.5 py-1.5 font-utility text-lg font-semibold tabular-nums shadow-lg ${
        isExplore ? "bg-explore-teal text-canvas" : "bg-signal-amber text-canvas"
      }`}
      title={isExplore ? "Exploration pick" : "Evidence-backed pick"}
    >
      {score === null ? "--" : Number(score).toFixed(2)}
      {isExplore && (
        <span className="ml-1.5 rounded bg-canvas/20 px-1 text-[10px] font-medium uppercase tracking-wide">
          Exp
        </span>
      )}
    </div>
  );
}
