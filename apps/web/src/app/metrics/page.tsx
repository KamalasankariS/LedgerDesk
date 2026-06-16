"use client";

import { useEffect, useState } from "react";
import { MetricCard } from "@/components/ui/MetricCard";
import { api } from "@/lib/api";
import type { DashboardMetrics } from "@/types";

const tracked = [
  "Workflow step timing", "Tool call latency", "Retrieval quality",
  "Fallback frequency", "Confidence distribution", "Override rate",
  "Recommendation acceptance", "Structured output validity", "Error counts",
];

export default function MetricsPage() {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.metrics.dashboard().then(setMetrics).catch(() => setMetrics(null)).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="card" style={{ height: 300 }} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        <MetricCard label="Total Cases"      value={metrics?.total_cases ?? 0} />
        <MetricCard label="Tool Invocations" value={metrics?.total_tool_invocations ?? 0}
          subtitle={metrics?.average_tool_latency_ms ? `${metrics.average_tool_latency_ms}ms avg` : undefined} />
        <MetricCard label="Avg Confidence"   value={metrics?.average_confidence ? `${Math.round(metrics.average_confidence * 100)}%` : "\u2014"} />
        <MetricCard label="Approval Rate"    value={metrics?.approval_rate ? `${Math.round(metrics.approval_rate * 100)}%` : "\u2014"} />
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        <MetricCard label="Agent Runs"   value={metrics?.total_agent_runs ?? 0} />
        <MetricCard label="Total Tokens" value={metrics?.total_tokens ? metrics.total_tokens.toLocaleString() : "0"} />
        <MetricCard label="Est. Cost"    value={metrics?.estimated_cost_usd != null ? `$${metrics.estimated_cost_usd.toFixed(4)}` : "$0.00"}
          subtitle="GPT-4o pricing" />
        <MetricCard label="Priority Dist."
          value={metrics?.cases_by_priority ? Object.entries(metrics.cases_by_priority).map(([k,v]) => `${k}: ${v}`).join(", ") : "\u2014"} />
      </div>

      <div className="card" style={{ padding: 0 }}>
        <div className="card-header">
          <h3>Tracked Metrics</h3>
          <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>captured per workflow run</span>
        </div>
        <div style={{ padding: "10px", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "6px 20px" }}>
          {tracked.map((m) => (
            <div key={m} style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span style={{ width: 6, height: 6, background: "#000080", flexShrink: 0, border: "1px solid #000" }} />
              <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#000" }}>{m}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
