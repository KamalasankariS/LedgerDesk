"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { showToast } from "@/components/ui/Toast";

interface EvalRun {
  id: string;
  run_type: string;
  status: string;
  total_cases: number;
  completed_cases: number;
  results_summary: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
}

export default function EvaluationPage() {
  const [runs, setRuns] = useState<EvalRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const loadRuns = () => {
    api.metrics
      .evaluations()
      .then((data: Record<string, unknown>) => setRuns((data as { runs: EvalRun[] }).runs || []))
      .catch(() => setRuns([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadRuns();
  }, []);

  const handleRun = async () => {
    setRunning(true);
    try {
      await api.metrics.runEvaluation();
      loadRuns();
    } catch (e: unknown) {
      showToast(e instanceof Error ? e.message : "Evaluation failed");
    }
    setRunning(false);
  };

  const latest = runs[0];

  if (loading) return <div className="card" style={{ height: 300 }} />;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mac-toolbar" style={{ justifyContent: "space-between" }}>
        <span style={{ fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold" }}>
          Evaluation Dashboard
        </span>
        <button onClick={handleRun} disabled={running} className="mac-btn-default">
          {running ? "Running..." : "Run Evaluation"}
        </button>
      </div>

      {latest && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          <div className="card" style={{ padding: "8px 10px", textAlign: "center" }}>
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", textTransform: "uppercase" }}>
              Latest Run
            </p>
            <p style={{ fontFamily: '"Monaco", monospace', fontSize: 16, fontWeight: "bold", color: "#000080" }}>
              {latest.run_type}
            </p>
          </div>
          <div className="card" style={{ padding: "8px 10px", textAlign: "center" }}>
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", textTransform: "uppercase" }}>
              Status
            </p>
            <p
              style={{
                fontFamily: '"Monaco", monospace',
                fontSize: 16,
                fontWeight: "bold",
                color: latest.status === "completed" ? "#006400" : "#8B6914",
              }}
            >
              {latest.status}
            </p>
          </div>
          <div className="card" style={{ padding: "8px 10px", textAlign: "center" }}>
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", textTransform: "uppercase" }}>
              Cases
            </p>
            <p style={{ fontFamily: '"Monaco", monospace', fontSize: 16, fontWeight: "bold" }}>
              {latest.completed_cases}/{latest.total_cases}
            </p>
          </div>
          <div className="card" style={{ padding: "8px 10px", textAlign: "center" }}>
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", textTransform: "uppercase" }}>
              Started
            </p>
            <p style={{ fontFamily: '"Monaco", monospace', fontSize: 11 }}>
              {new Date(latest.started_at).toLocaleString()}
            </p>
          </div>
        </div>
      )}

      <div className="card" style={{ padding: 0 }}>
        <div className="card-header" style={{ justifyContent: "space-between" }}>
          <h3>Evaluation History</h3>
          <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>
            {runs.length} runs
          </span>
        </div>
        {runs.length === 0 ? (
          <p
            style={{
              padding: "20px 10px",
              fontFamily: '"Geneva", sans-serif',
              fontSize: 11,
              color: "#888",
              textAlign: "center",
            }}
          >
            No evaluation runs yet. Click &quot;Run Evaluation&quot; to start.
          </p>
        ) : (
          <div>
            {runs.map((run) => (
              <div key={run.id} style={{ borderBottom: "1px solid #D4D0C8" }}>
                <div
                  onClick={() => setExpandedId(expandedId === run.id ? null : run.id)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "100px 80px 80px 1fr 40px",
                    gap: 8,
                    padding: "6px 10px",
                    cursor: "pointer",
                    alignItems: "center",
                  }}
                >
                  <span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#000080", fontWeight: "bold" }}>
                    {run.run_type}
                  </span>
                  <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, display: "flex", alignItems: "center", gap: 4 }}>
                    <span
                      style={{
                        display: "inline-block",
                        width: 6,
                        height: 6,
                        borderRadius: "50%",
                        background:
                          run.status === "completed"
                            ? "#006400"
                            : run.status === "running"
                              ? "#8B6914"
                              : "#880000",
                      }}
                    />
                    {run.status}
                  </span>
                  <span style={{ fontFamily: '"Monaco", monospace', fontSize: 10 }}>
                    {run.completed_cases}/{run.total_cases}
                  </span>
                  <span style={{ fontFamily: '"Monaco", monospace', fontSize: 9, color: "#888" }}>
                    {new Date(run.started_at).toLocaleString()}
                  </span>
                  <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000080", textAlign: "right" }}>
                    {expandedId === run.id ? "v" : ">"}
                  </span>
                </div>
                {expandedId === run.id && run.results_summary && (
                  <div className="mac-inset" style={{ margin: "0 10px 8px", padding: 8 }}>
                    <pre style={{ fontFamily: '"Monaco", monospace', fontSize: 10, whiteSpace: "pre-wrap", color: "#000", margin: 0 }}>
                      {JSON.stringify(run.results_summary, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
