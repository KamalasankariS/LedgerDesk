interface ConfidenceIndicatorProps {
  score: number;
  showLabel?: boolean;
  size?: "sm" | "md";
}

export function ConfidenceIndicator({ score, showLabel = true, size = "md" }: ConfidenceIndicatorProps) {
  const pct   = Math.round(score * 100);
  const color = pct >= 85 ? "#006400" : pct >= 70 ? "#8B6914" : "#8B0000";
  const width = size === "sm" ? 64 : 96;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div className="mac-progress" style={{ width }}>
        <div className="mac-progress-fill" style={{ width: `${pct}%` }} />
      </div>
      {showLabel && (
        <span style={{ fontFamily: '"Monaco", monospace', fontSize: 11, fontWeight: "bold", color, fontVariantNumeric: "tabular-nums" }}>
          {pct}%
        </span>
      )}
    </div>
  );
}
