"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Badge } from "@/components/ui/Badge";
import { ConfidenceIndicator } from "@/components/ui/ConfidenceIndicator";
import { api } from "@/lib/api";
import { showToast } from "@/components/ui/Toast";
import type { Case, Recommendation } from "@/types";

const WORKFLOW_STEPS = ["Triage", "Retrieval", "Tool Planning", "Tool Execution", "Decision", "Safety Gate", "Complete"];

/* -- Reason Modal ---------------------------------------------------- */
function ReasonModal({ type, onConfirm, onCancel }: { type: "escalate" | "reject"; onConfirm: (r: string) => void; onCancel: () => void }) {
  const [reason, setReason] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const isEsc = type === "escalate";

  useEffect(() => {
    ref.current?.focus();
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onCancel(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [onCancel]);

  return (
    <div className="mac-modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onCancel(); }}>
      <div className="mac-dialog" style={{ width: 420 }}>
        <div className="mac-dialog-titlebar">
          <span className="mac-widget" onClick={onCancel} />
          <span style={{ flex: 1, textAlign: "center", fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold" }}>
            {isEsc ? "Escalate Case" : "Reject Case"}
          </span>
        </div>
        <div className="mac-dialog-body">
          <label className="mac-label">{isEsc ? "Escalation Reason" : "Rejection Reason"} *</label>
          <textarea
            ref={ref}
            rows={4}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder={isEsc ? "e.g. Requires supervisor review..." : "e.g. Conflicts with customer history..."}
            className="mac-input"
          />
          <p style={{ fontSize: 10, color: "#888", fontFamily: '"Geneva", sans-serif', marginTop: 4 }}>
            This reason will be recorded in the audit trail.
          </p>
        </div>
        <div className="mac-dialog-footer">
          <button onClick={onCancel} className="mac-btn">Cancel</button>
          <button
            onClick={() => { if (reason.trim()) onConfirm(reason.trim()); }}
            disabled={!reason.trim()}
            className={isEsc ? "mac-btn-default" : "mac-btn-danger"}
          >
            {isEsc ? "Escalate" : "Reject"}
          </button>
        </div>
      </div>
    </div>
  );
}

/* -- Step Progress Bar ----------------------------------------------- */
function StepProgress({ completedSteps, running }: { completedSteps: string[]; running: boolean }) {
  return (
    <div style={{ display: "flex", gap: 2, padding: "8px 10px" }}>
      {WORKFLOW_STEPS.map((step) => {
        const done = completedSteps.includes(step);
        const isActive = running && !done && completedSteps.length > 0 && WORKFLOW_STEPS[completedSteps.length] === step;
        return (
          <div
            key={step}
            style={{
              flex: 1,
              textAlign: "center",
              padding: "4px 2px",
              fontSize: 9,
              fontFamily: '"Geneva", sans-serif',
              fontWeight: done ? "bold" : "normal",
              color: done ? "#FFF" : isActive ? "#000080" : "#888",
              background: done ? "#000080" : isActive ? "#E8E8FF" : "#D4D0C8",
              border: "1px solid",
              borderColor: done ? "#000060" : "#A0A0A0",
              borderRight: "none",
              transition: "all 0.3s ease",
            }}
          >
            {step}
          </div>
        );
      })}
    </div>
  );
}

/* -- Case Detail Page ------------------------------------------------ */
export default function CaseDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [caseData, setCaseData]     = useState<Case | null>(null);
  const [recs, setRecs]             = useState<Recommendation[]>([]);
  const [history, setHistory]       = useState<{ id: string; from_status: string | null; to_status: string; created_at: string }[]>([]);
  const [notes, setNotes]           = useState<{ id: string; content: string; created_at: string }[]>([]);
  const [loading, setLoading]       = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [newNote, setNewNote]       = useState("");
  const [workflowRunning, setWorkflowRunning] = useState(false);
  const [workflowResult, setWorkflowResult]   = useState<{ status?: string; steps?: { step: string }[] } | null>(null);
  const [reasonModal, setReasonModal] = useState<"escalate" | "reject" | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);

  const loadData = useRef(() => {});
  loadData.current = () => {
    Promise.all([api.cases.get(id), api.cases.recommendations(id), api.cases.history(id), api.cases.notes(id)])
      .then(([c, r, h, n]) => { setCaseData(c); setRecs(r); setHistory(h); setNotes(n); })
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData.current(); }, [id]);

  const submitAction = async (actionType: string, reason?: string) => {
    setActionLoading(true);
    try {
      await api.cases.action(id, { action_type: actionType, recommendation_id: recs[0]?.id || null, reason });
      loadData.current();
    } catch (e: unknown) { showToast(e instanceof Error ? e.message : "Action failed"); }
    setActionLoading(false);
  };

  const handleAction = (t: string) => {
    if (t === "escalate" || t === "reject") setReasonModal(t as "escalate" | "reject");
    else submitAction(t);
  };

  const handleRunWorkflow = async () => {
    setWorkflowRunning(true);
    setCompletedSteps([]);
    setWorkflowResult(null);

    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";
      const res = await fetch(`${API_BASE}/api/v1/workflow/run/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ case_id: id }),
      });

      if (!res.ok || !res.body) throw new Error("Stream unavailable");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const event = JSON.parse(line.slice(6));
            if (event.step === "done") {
              setWorkflowResult({ status: event.status });
            } else {
              setCompletedSteps((prev) =>
                prev.includes(event.step) ? prev : [...prev, event.step]
              );
            }
          } catch {
            // skip malformed events
          }
        }
      }
      loadData.current();
    } catch {
      // Fallback to non-streaming endpoint
      try {
        const r = await api.workflow.run(id);
        setWorkflowResult({ status: r.status, steps: r.steps as { step: string }[] });
        setCompletedSteps(WORKFLOW_STEPS);
        loadData.current();
      } catch (e: unknown) {
        showToast(e instanceof Error ? e.message : "Workflow failed");
      }
    }
    setWorkflowRunning(false);
  };

  const handleAddNote = async () => {
    if (!newNote.trim()) return;
    await api.cases.addNote(id, { content: newNote, note_type: "general" });
    setNewNote(""); loadData.current();
  };

  if (loading) return <div className="card" style={{ height: 300 }} />;
  if (!caseData) return <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 12, padding: 20, color: "#555" }}>Case not found.</p>;

  const latestRec = recs[0];
  const labelStyle: React.CSSProperties = {
    fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555",
    textTransform: "uppercase", letterSpacing: "0.05em", fontWeight: "bold",
  };

  return (
    <>
      {reasonModal && (
        <ReasonModal
          type={reasonModal}
          onConfirm={(reason) => { setReasonModal(null); submitAction(reasonModal, reason); }}
          onCancel={() => setReasonModal(null)}
        />
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {/* Back + header */}
        <div className="mac-toolbar" style={{ justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <button onClick={() => router.push("/cases")} className="mac-btn" style={{ minWidth: 0, padding: "2px 8px" }}>
              &larr; Back
            </button>
            <span style={{ fontFamily: '"Monaco", monospace', fontSize: 11, color: "#555" }}>{caseData.case_number}</span>
            <span style={{ fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold", color: "#000" }}>
              {caseData.title}
            </span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            <Badge type="status" value={caseData.status} />
            <Badge type="priority" value={caseData.priority} />
          </div>
        </div>

        {/* Two-column body */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 220px", gap: 8 }}>
          {/* Left */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>

            {/* Description */}
            <div className="card" style={{ padding: 0 }}>
              <div className="card-header"><h3>Case Description</h3></div>
              <p style={{ padding: "8px 10px", fontFamily: '"Geneva", sans-serif', fontSize: 12, lineHeight: 1.6, color: "#000" }}>
                {caseData.description}
              </p>
            </div>

            {/* Run Workflow */}
            {caseData.status === "created" && (
              <div className="card" style={{ padding: 0 }}>
                <div className="card-header"><h3>Agent Workflow</h3></div>
                <div style={{ padding: "8px 10px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#555" }}>
                    Triage, retrieve context, execute tools, and generate a recommendation.
                  </p>
                  <button onClick={handleRunWorkflow} disabled={workflowRunning} className="mac-btn-default">
                    {workflowRunning ? "Running..." : "Run Workflow"}
                  </button>
                </div>
                {(workflowRunning || completedSteps.length > 0) && (
                  <StepProgress completedSteps={completedSteps} running={workflowRunning} />
                )}
                {workflowResult && (
                  <div style={{ padding: "0 10px 8px", borderTop: "1px solid #D4D0C8" }}>
                    <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: workflowResult.status === "failed" ? "#880000" : "#555", margin: "6px 0 4px" }}>
                      {workflowResult.status === "failed" ? "Workflow failed" : `Completed -- ${workflowResult.steps?.length || completedSteps.length} steps`}
                    </p>
                  </div>
                )}
              </div>
            )}

            {/* Recommendation */}
            {latestRec && (
              <div className="card" style={{ padding: 0, borderLeft: "3px solid #000080" }}>
                {/* Header */}
                <div className="card-header" style={{ justifyContent: "space-between" }}>
                  <h3>System Recommendation</h3>
                  <ConfidenceIndicator score={latestRec.confidence_score} />
                </div>

                {/* Analyst Summary */}
                {latestRec.analyst_summary && (
                  <div style={{ background: "#FFFFF0", borderBottom: "1px solid #8B6914", padding: "8px 10px" }}>
                    <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#8B6914", fontWeight: "bold", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: 3 }}>
                      Analyst Briefing
                    </p>
                    <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#000", lineHeight: 1.6 }}>
                      {latestRec.analyst_summary}
                    </p>
                  </div>
                )}

                <div style={{ padding: "10px", display: "flex", flexDirection: "column", gap: 12 }}>

                  {/* Action + structured decision metadata */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
                    <div>
                      <p style={labelStyle}>Recommended Action</p>
                      <p style={{ fontFamily: '"Monaco", monospace', fontSize: 13, fontWeight: "bold", color: "#000080", marginTop: 2 }}>
                        {latestRec.recommended_action?.replace(/_/g, " ").toUpperCase()}
                      </p>
                    </div>
                    {latestRec.structured_decision && (() => {
                      const sd = latestRec.structured_decision as Record<string, string | number | boolean>;
                      return (
                      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                        <p style={labelStyle}>Decision Details</p>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                          <span className={`badge ${sd.risk_level === "high" ? "badge-red" : sd.risk_level === "medium" ? "badge-yellow" : "badge-green"}`}>
                            Risk: {String(sd.risk_level)}
                          </span>
                          <span className="badge badge-blue">
                            ~{String(sd.estimated_resolution_days)}d resolution
                          </span>
                          {sd.requires_merchant_contact && (
                            <span className="badge badge-yellow">Merchant contact required</span>
                          )}
                          {sd.requires_cardholder_notification && (
                            <span className="badge badge-blue">Cardholder notification required</span>
                          )}
                        </div>
                      </div>);
                    })()}
                  </div>

                  <hr />

                  {/* Rationale */}
                  <div>
                    <p style={labelStyle}>Analysis &amp; Rationale</p>
                    <div style={{ marginTop: 6 }}>
                      {(latestRec.rationale || "").split("\n\n").map((para: string, i: number) => (
                        para.trim() ? (
                          <p key={i} style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#000", lineHeight: 1.7, marginBottom: 8 }}>
                            {para.trim()}
                          </p>
                        ) : null
                      ))}
                    </div>
                  </div>

                  <hr />

                  {/* Evidence Summary */}
                  {latestRec.evidence_summary && (() => {
                    const es = latestRec.evidence_summary as { supporting?: string[]; concerning?: string[]; missing?: string[] };
                    return (
                    <div>
                      <p style={labelStyle}>Evidence Summary</p>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginTop: 6 }}>
                        <div>
                          <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, fontWeight: "bold", color: "#006400", marginBottom: 4 }}>
                            Supporting ({es.supporting?.length ?? 0})
                          </p>
                          {(es.supporting || []).map((e, i) => (
                            <div key={i} style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000", background: "#F0FFF0", border: "1px solid #006400", padding: "3px 6px", marginBottom: 3, lineHeight: 1.5 }}>
                              {e}
                            </div>
                          ))}
                        </div>
                        <div>
                          <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, fontWeight: "bold", color: "#8B6914", marginBottom: 4 }}>
                            Concerning ({es.concerning?.length ?? 0})
                          </p>
                          {(es.concerning || []).length === 0 ? (
                            <div style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#888", fontStyle: "italic" }}>None identified</div>
                          ) : (es.concerning || []).map((e, i) => (
                            <div key={i} style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000", background: "#FFFFF0", border: "1px solid #8B6914", padding: "3px 6px", marginBottom: 3, lineHeight: 1.5 }}>
                              {e}
                            </div>
                          ))}
                        </div>
                        <div>
                          <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, fontWeight: "bold", color: "#880000", marginBottom: 4 }}>
                            Missing ({es.missing?.length ?? 0})
                          </p>
                          {(es.missing || []).length === 0 ? (
                            <div style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#888", fontStyle: "italic" }}>None identified</div>
                          ) : (es.missing || []).map((e, i) => (
                            <div key={i} style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000", background: "#FFE8E8", border: "1px solid #880000", padding: "3px 6px", marginBottom: 3, lineHeight: 1.5 }}>
                              {e}
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>);
                  })()}

                  <hr />

                  {/* Policy Citations from RAG */}
                  {latestRec.policy_citations && latestRec.policy_citations.length > 0 && (
                    <div>
                      <p style={labelStyle}>Policy Citations (Retrieved via RAG)</p>
                      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginTop: 6 }}>
                        {latestRec.policy_citations.map((c, i: number) => {
                          const cit = c as Record<string, string>;
                          if (typeof c === "string") {
                            return (
                              <div key={i} className="mac-inset" style={{ fontSize: 10 }}>{c as string}</div>
                            );
                          }
                          return (
                            <div key={i} style={{ background: "#E8E8FF", border: "1px solid #000080", padding: "8px 10px" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                                <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, fontWeight: "bold", color: "#000080" }}>
                                  {cit.document}
                                </p>
                                <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 9, color: "#000080" }}>
                                  {cit.section}
                                </p>
                              </div>
                              {cit.quote && (
                                <blockquote style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#333", borderLeft: "2px solid #000080", paddingLeft: 8, margin: "4px 0", lineHeight: 1.6, fontStyle: "italic" }}>
                                  &quot;{cit.quote}&quot;
                                </blockquote>
                              )}
                              {cit.relevance && (
                                <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", marginTop: 6, textAlign: "center" }}>
                                  - {cit.relevance}
                                </p>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}

                </div>
              </div>
            )}

            {/* Analyst Decision */}
            {(caseData.status === "awaiting_review" || caseData.status === "safety_checked") && (
              <div className="card" style={{ padding: 0 }}>
                <div className="card-header"><h3>Analyst Decision</h3></div>
                <div style={{ padding: "8px 10px", display: "flex", gap: 8 }}>
                  <button onClick={() => handleAction("approve")} disabled={actionLoading} className="mac-btn-default">Approve</button>
                  <button onClick={() => handleAction("reject")}  disabled={actionLoading} className="mac-btn-danger">Reject</button>
                  <button onClick={() => handleAction("escalate")} disabled={actionLoading} className="mac-btn">Escalate</button>
                </div>
              </div>
            )}

            {/* Notes */}
            <div className="card" style={{ padding: 0 }}>
              <div className="card-header"><h3>Analyst Notes</h3></div>
              <div style={{ padding: "8px 10px" }}>
                <div style={{ display: "flex", gap: 6, marginBottom: 8 }}>
                  <input
                    type="text"
                    className="mac-input"
                    style={{ flex: 1 }}
                    placeholder="Add a note..."
                    value={newNote}
                    onChange={(e) => setNewNote(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleAddNote()}
                  />
                  <button onClick={handleAddNote} className="mac-btn" style={{ minWidth: 0, padding: "2px 10px" }}>Add</button>
                </div>
                {notes.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                    {notes.map((n) => (
                      <div key={n.id} className="mac-inset" style={{ fontSize: 11 }}>
                        <p style={{ fontFamily: '"Geneva", sans-serif', color: "#000" }}>{n.content}</p>
                        <p style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555", marginTop: 2 }}>
                          {new Date(n.created_at).toLocaleString()}
                        </p>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#888" }}>No notes yet.</p>
                )}
              </div>
            </div>
          </div>

          {/* Right column */}
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {/* Case Info */}
            <div className="card" style={{ padding: 0 }}>
              <div className="card-header"><h3>Case Information</h3></div>
              <dl style={{ padding: "6px 10px" }}>
                {[
                  ["Issue Type",   caseData.issue_type?.replace(/_/g, " ") || "Unclassified"],
                  ["Transaction",  caseData.transaction_id || "\u2014"],
                  ["Account",      caseData.account_id || "\u2014"],
                  ["Merchant",     caseData.merchant_name || "\u2014"],
                  ["Amount",       caseData.amount ? `$${Number(caseData.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "\u2014"],
                  ["Currency",     caseData.currency],
                  ["Trace ID",     caseData.trace_id?.slice(0, 8) + "\u2026" || "\u2014"],
                ].map(([label, value]) => (
                  <div key={label} style={{ display: "flex", justifyContent: "space-between", padding: "3px 0", borderBottom: "1px solid #F0F0F0" }}>
                    <dt style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>{label}</dt>
                    <dd style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#000" }}>{value}</dd>
                  </div>
                ))}
              </dl>
            </div>

            {/* Status History */}
            <div className="card" style={{ padding: 0 }}>
              <div className="card-header"><h3>Status History</h3></div>
              <div style={{ padding: "6px 10px" }}>
                {history.length > 0 ? (
                  history.map((h, i) => (
                    <div key={h.id || i} style={{ display: "flex", gap: 6, alignItems: "flex-start", paddingBottom: 6, marginBottom: 6, borderBottom: i < history.length - 1 ? "1px solid #D4D0C8" : "none" }}>
                      <span style={{ color: "#000080", fontSize: 10, marginTop: 1 }}>&#9654;</span>
                      <div>
                        <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000" }}>
                          {h.from_status ? `${h.from_status} \u2192 ` : ""}{h.to_status}
                        </p>
                        <p style={{ fontFamily: '"Monaco", monospace', fontSize: 9, color: "#888" }}>
                          {new Date(h.created_at).toLocaleString()}
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#888", padding: "4px 0" }}>No history yet.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
