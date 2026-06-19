"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import type { Case } from "@/types";

/* ── New Case Modal ───────────────────────────────────────────── */
function NewCaseModal({ onClose, onCreated }: { onClose: () => void; onCreated: (id: string) => void }) {
  const firstRef = useRef<HTMLInputElement>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "", description: "", priority: "medium", issue_type: "",
    transaction_id: "", account_id: "", merchant_name: "", amount: "", currency: "USD",
  });

  useEffect(() => {
    firstRef.current?.focus();
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const set = (k: keyof typeof form) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.title.trim() || !form.description.trim()) return;
    setSubmitting(true); setError(null);
    try {
      const created = await api.cases.create({
        title: form.title.trim(),
        description: form.description.trim(),
        priority: form.priority,
        currency: form.currency || "USD",
        ...(form.issue_type     && { issue_type: form.issue_type }),
        ...(form.transaction_id && { transaction_id: form.transaction_id.trim() }),
        ...(form.account_id     && { account_id: form.account_id.trim() }),
        ...(form.merchant_name  && { merchant_name: form.merchant_name.trim() }),
        ...(form.amount         && { amount: parseFloat(form.amount) }),
      });
      onCreated(created.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to create case.");
      setSubmitting(false);
    }
  };

  return (
    <div className="mac-modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="mac-dialog" style={{ width: 480, maxHeight: "90vh", display: "flex", flexDirection: "column" }}>
        {/* Title bar */}
        <div className="mac-dialog-titlebar">
          <span className="mac-widget" onClick={onClose} />
          <span style={{ flex: 1, textAlign: "center", fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold" }}>
            New Case
          </span>
        </div>

        {/* Scrollable body */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
          <div style={{ padding: "14px 18px", overflowY: "auto", flex: 1 }}>

            <div style={{ marginBottom: 10 }}>
              <label className="mac-label">Title *</label>
              <input ref={firstRef} type="text" value={form.title} onChange={set("title")}
                placeholder="e.g. Duplicate charge — Amazon Prime" required className="mac-input" />
            </div>

            <div style={{ marginBottom: 10 }}>
              <label className="mac-label">Description *</label>
              <textarea rows={3} value={form.description} onChange={set("description")}
                placeholder="Describe the exception…" required className="mac-input" />
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              <div>
                <label className="mac-label">Priority</label>
                <select value={form.priority} onChange={set("priority")} className="mac-input">
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div>
                <label className="mac-label">Issue Type</label>
                <select value={form.issue_type} onChange={set("issue_type")} className="mac-input">
                  <option value="">— Select —</option>
                  <option value="duplicate_charge">Duplicate Charge</option>
                  <option value="refund_reversal">Refund / Reversal</option>
                  <option value="pending_authorization">Pending Authorization</option>
                  <option value="settlement_delay">Settlement Delay</option>
                  <option value="escalation">Escalation</option>
                  <option value="other">Other</option>
                </select>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 10 }}>
              <div>
                <label className="mac-label">Transaction ID</label>
                <input type="text" value={form.transaction_id} onChange={set("transaction_id")}
                  placeholder="TXN-XXXXXXXX" className="mac-input" />
              </div>
              <div>
                <label className="mac-label">Account ID</label>
                <input type="text" value={form.account_id} onChange={set("account_id")}
                  placeholder="ACCT-XXXXXXXX" className="mac-input" />
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 10, marginBottom: 10 }}>
              <div>
                <label className="mac-label">Merchant</label>
                <input type="text" value={form.merchant_name} onChange={set("merchant_name")}
                  placeholder="e.g. Amazon" className="mac-input" />
              </div>
              <div>
                <label className="mac-label">Amount</label>
                <input type="number" min="0" step="0.01" value={form.amount} onChange={set("amount")}
                  placeholder="0.00" className="mac-input" />
              </div>
              <div>
                <label className="mac-label">Currency</label>
                <select value={form.currency} onChange={set("currency")} className="mac-input">
                  <option>USD</option><option>EUR</option><option>GBP</option><option>CAD</option>
                </select>
              </div>
            </div>

            {error && (
              <div style={{ background: "#FFE8E8", border: "1px solid #880000", color: "#880000", padding: "4px 8px", fontSize: 11, fontFamily: '"Geneva", sans-serif' }}>
                ⚠ {error}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="mac-dialog-footer">
            <p style={{ fontSize: 10, color: "#888", fontFamily: '"Geneva", sans-serif', marginRight: "auto" }}>
              Status starts as <em>created</em>.
            </p>
            <button type="button" onClick={onClose} className="mac-btn">Cancel</button>
            <button type="submit" disabled={submitting || !form.title.trim() || !form.description.trim()} className="mac-btn-default">
              {submitting ? "Creating…" : "Create Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

/* ── Case Queue Page ──────────────────────────────────────────── */
export default function CaseQueuePage() {
  const router = useRouter();
  const [cases, setCases]               = useState<Case[]>([]);
  const [total, setTotal]               = useState(0);
  const [loading, setLoading]           = useState(true);
  const [search, setSearch]             = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [priorityFilter, setPriorityFilter] = useState("");
  const [showNewCase, setShowNewCase]   = useState(false);

  useEffect(() => { document.title = "Case Queue — LedgerDesk"; }, []);

  useEffect(() => {
    const params: Record<string, string> = {};
    if (search)         params.search   = search;
    if (statusFilter)   params.status   = statusFilter;
    if (priorityFilter) params.priority = priorityFilter;
    api.cases.list(params)
      .then((data) => { setCases(data.cases || []); setTotal(data.total || 0); })
      .catch(() => setCases([]))
      .finally(() => setLoading(false));
  }, [search, statusFilter, priorityFilter]);

  const handleCreated = (id: string) => { setShowNewCase(false); router.push(`/cases/${id}`); };

  return (
    <>
      {showNewCase && <NewCaseModal onClose={() => setShowNewCase(false)} onCreated={handleCreated} />}

      <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
        {/* Mac Toolbar */}
        <div className="mac-toolbar">
          <input type="text" placeholder="Search cases…" className="mac-input" style={{ width: 180 }}
            value={search} onChange={(e) => setSearch(e.target.value)} />
          <select className="mac-input" style={{ width: 150 }} value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
            <option value="">All Statuses</option>
            <option value="created">Created</option>
            <option value="triaged">Triaged</option>
            <option value="awaiting_review">Awaiting Review</option>
            <option value="approved">Approved</option>
            <option value="escalated">Escalated</option>
            <option value="completed">Completed</option>
          </select>
          <select className="mac-input" style={{ width: 130 }} value={priorityFilter} onChange={(e) => setPriorityFilter(e.target.value)}>
            <option value="">All Priorities</option>
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="critical">Critical</option>
          </select>
          <span style={{ marginLeft: "auto", fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#555" }}>
            {total} case{total !== 1 ? "s" : ""}
          </span>
          <button onClick={() => setShowNewCase(true)} className="mac-btn-default">
            + New Case
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="skeleton" style={{ height: 200 }} />
        ) : cases.length === 0 ? (
          <EmptyState title="No cases found" description="Adjust your filters or create a new case."
            action={<button onClick={() => setShowNewCase(true)} className="mac-btn-default">New Case</button>} />
        ) : (
          <div className="card p-0" style={{ overflow: "hidden" }}>
            <table className="mac-list" style={{ width: "100%" }}>
              <thead>
                <tr>
                  <th>Case #</th>
                  <th>Title</th>
                  <th>Status</th>
                  <th>Priority</th>
                  <th>Type</th>
                  <th style={{ textAlign: "right" }}>Amount</th>
                  <th>Created</th>
                </tr>
              </thead>
              <tbody>
                {cases.map((c) => (
                  <tr key={c.id} style={{ cursor: "default" }}>
                    <td>
                      <Link href={`/cases/${c.id}`} style={{ fontFamily: '"Monaco", monospace', fontSize: 11, color: "#000080", textDecoration: "none" }}>
                        {c.case_number}
                      </Link>
                    </td>
                    <td>
                      <Link href={`/cases/${c.id}`} style={{ color: "#000", textDecoration: "none", fontSize: 11 }}>
                        {c.title}
                      </Link>
                    </td>
                    <td><Badge type="status" value={c.status} /></td>
                    <td><Badge type="priority" value={c.priority} /></td>
                    <td style={{ color: "#555" }}>{c.issue_type?.replace(/_/g, " ") || "—"}</td>
                    <td style={{ textAlign: "right", fontFamily: '"Monaco", monospace', fontSize: 11 }}>
                      {c.amount ? `$${Number(c.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—"}
                    </td>
                    <td style={{ color: "#555" }}>{new Date(c.created_at).toLocaleDateString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </>
  );
}
