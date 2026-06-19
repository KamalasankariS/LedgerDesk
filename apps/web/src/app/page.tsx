"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MetricCard } from "@/components/ui/MetricCard";
import { Badge }      from "@/components/ui/Badge";
import { api }        from "@/lib/api";
import { showToast }  from "@/components/ui/Toast";
import type { DashboardMetrics } from "@/types";

export default function DashboardPage() {
  const router = useRouter();
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);

  useEffect(() => { document.title = "Dashboard — LedgerDesk"; }, []);

  useEffect(() => {
    api.metrics.dashboard().then(setMetrics).catch(() => setMetrics(null)).finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          {[...Array(4)].map((_, i) => <div key={i} className="skeleton" style={{ height: 80 }} />)}
        </div>
        <div className="skeleton" style={{ height: 120 }} />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Metric cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
        <MetricCard label="Total Cases"     value={metrics?.total_cases ?? 0} subtitle="All time" />
        <MetricCard label="Avg Confidence"  value={metrics?.average_confidence ? `${Math.round(metrics.average_confidence * 100)}%` : "—"} subtitle="AI recommendation score" />
        <MetricCard label="Tool Invocations" value={metrics?.total_tool_invocations ?? 0} subtitle={metrics?.average_tool_latency_ms ? `${metrics.average_tool_latency_ms}ms avg` : "All time"} />
        <MetricCard label="Approval Rate"   value={metrics?.approval_rate ? `${Math.round(metrics.approval_rate * 100)}%` : "—"} subtitle="Analyst acceptance" />
      </div>

      {/* Status distribution */}
      {metrics?.cases_by_status && Object.keys(metrics.cases_by_status).length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div className="card-header">
            <h3>Cases by Status</h3>
            <span style={{ fontFamily: '"Geneva",sans-serif', fontSize: 10, color: "#555" }}>click to filter</span>
          </div>
          <div style={{ padding: "8px 10px", display: "flex", flexWrap: "wrap", gap: 10 }}>
            {Object.entries(metrics.cases_by_status).map(([status, count]) => (
              <button
                key={status}
                onClick={() => router.push(`/cases?status=${encodeURIComponent(status)}`)}
                style={{ background: "none", border: "none", padding: 0, display: "flex", alignItems: "center", gap: 6, cursor: "default" }}
                title={`View ${status} cases`}
              >
                <Badge type="status" value={status} />
                <span style={{ fontFamily: '"Monaco",monospace', fontSize: 11, color: "#333" }}>{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Agent / Token summary */}
      {metrics && metrics.total_agent_runs > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8 }}>
          <MetricCard label="Agent Runs"   value={metrics.total_agent_runs} subtitle="LLM calls" />
          <MetricCard label="Total Tokens" value={metrics.total_tokens ? metrics.total_tokens.toLocaleString() : "0"} subtitle="prompt + completion" />
          <MetricCard label="Est. Cost"    value={`$${(metrics.estimated_cost_usd ?? 0).toFixed(4)}`} subtitle="GPT-4o pricing" />
        </div>
      )}

      {/* Priority distribution */}
      {metrics?.cases_by_priority && Object.keys(metrics.cases_by_priority).length > 0 && (
        <div className="card" style={{ padding: 0 }}>
          <div className="card-header">
            <h3>Cases by Priority</h3>
            <span style={{ fontFamily: '"Geneva",sans-serif', fontSize: 10, color: "#555" }}>click to filter</span>
          </div>
          <div style={{ padding: "8px 10px", display: "flex", flexWrap: "wrap", gap: 10 }}>
            {Object.entries(metrics.cases_by_priority).map(([priority, count]) => (
              <button
                key={priority}
                onClick={() => router.push(`/cases?priority=${encodeURIComponent(priority)}`)}
                style={{ background: "none", border: "none", padding: 0, display: "flex", alignItems: "center", gap: 6, cursor: "default" }}
                title={`View ${priority} priority cases`}
              >
                <Badge type="priority" value={priority} />
                <span style={{ fontFamily: '"Monaco",monospace', fontSize: 11, color: "#333" }}>{count}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Welcome / empty state */}
      {(!metrics || metrics.total_cases === 0) && (
        <div className="card" style={{ textAlign: "center", padding: "40px 20px" }}>
          <div style={{
            width: 48, height: 48, margin: "0 auto 12px",
            background: "#000080", border: "2px solid #000",
            boxShadow: "inset 1px 1px 0 #4444AA, inset -1px -1px 0 #000040",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: '"Chicago",sans-serif', fontSize: 14, fontWeight: "bold", color: "#fff",
          }}>
            LD
          </div>
          <p style={{ fontFamily: '"Chicago","Charcoal",sans-serif', fontSize: 13, fontWeight: "bold", color: "#000", marginBottom: 6 }}>
            Welcome to LedgerDesk
          </p>
          <p style={{ fontFamily: '"Geneva",sans-serif', fontSize: 11, color: "#555", maxWidth: 320, margin: "0 auto" }}>
            Agentic financial operations copilot for transaction exception handling and policy-grounded case resolution.
          </p>
          <button
            disabled={seeding}
            className="mac-btn-default"
            style={{ marginTop: 14 }}
            onClick={async () => {
              setSeeding(true);
              try {
                const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
                const res = await fetch(`${API_BASE}/api/v1/seed`, { method: "POST" });
                if (!res.ok) throw new Error("Seed failed");
                showToast("Demo data seeded successfully!", "success");
                api.metrics.dashboard().then(setMetrics).catch(() => setMetrics(null));
              } catch {
                showToast("Failed to seed database. Is the API running?", "error");
              } finally { setSeeding(false); }
            }}
          >
            {seeding ? "Seeding..." : "Seed Demo Data"}
          </button>
        </div>
      )}
    </div>
  );
}
