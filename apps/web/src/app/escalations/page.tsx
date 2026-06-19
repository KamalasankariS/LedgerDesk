"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { EmptyState } from "@/components/ui/EmptyState";
import { api } from "@/lib/api";
import type { Case } from "@/types";

export default function EscalationsPage() {
  const [cases, setCases]     = useState<Case[]>([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);

  const load = () => {
    setLoading(true);
    api.cases.list({ status: "escalated" })
      .then((data) => { setCases(data.cases || []); setTotal(data.total || 0); })
      .catch(() => setCases([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => { document.title = "Escalations — LedgerDesk"; }, []);
  useEffect(() => { load(); }, []);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      {/* Toolbar */}
      <div className="mac-toolbar" style={{ justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#555" }}>
            Cases escalated by analysts requiring supervisor review
          </span>
          <span className="badge badge-escalated">{total} pending</span>
        </div>
        <button onClick={load} className="mac-btn">Refresh</button>
      </div>

      {/* Warning banner */}
      <div style={{ background: "#FFFFF0", border: "1px solid #8B6914", color: "#8B6914", padding: "6px 10px", fontFamily: '"Geneva", sans-serif', fontSize: 11 }}>
        ▲ <strong>Supervisor action required.</strong> These cases are awaiting your review. Open each case to view context and take action.
      </div>

      {/* Table */}
      {loading ? (
        <div className="skeleton" style={{ height: 200 }} />
      ) : cases.length === 0 ? (
        <EmptyState title="No escalated cases" description="All clear — no cases are currently awaiting supervisor review." />
      ) : (
        <div className="card p-0" style={{ overflow: "hidden" }}>
          <table className="mac-list" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>Case #</th>
                <th>Title</th>
                <th>Priority</th>
                <th>Issue Type</th>
                <th style={{ textAlign: "right" }}>Amount</th>
                <th>Merchant</th>
                <th>Escalated</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {cases.map((c) => (
                <tr key={c.id}>
                  <td><span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555" }}>{c.case_number}</span></td>
                  <td>
                    <Link href={`/cases/${c.id}`} style={{ color: "#000080", textDecoration: "none", fontSize: 11 }}>
                      {c.title}
                    </Link>
                  </td>
                  <td><Badge type="priority" value={c.priority} /></td>
                  <td style={{ color: "#555" }}>{c.issue_type?.replace(/_/g, " ") || "—"}</td>
                  <td style={{ textAlign: "right", fontFamily: '"Monaco", monospace', fontSize: 10 }}>
                    {c.amount ? `$${Number(c.amount).toLocaleString("en-US", { minimumFractionDigits: 2 })}` : "—"}
                  </td>
                  <td style={{ color: "#555" }}>{c.merchant_name || "—"}</td>
                  <td style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555" }}>
                    {new Date(c.updated_at ?? c.created_at).toLocaleString()}
                  </td>
                  <td>
                    <Link href={`/cases/${c.id}`} className="mac-btn-default" style={{ fontSize: 10, minWidth: 0, padding: "2px 8px", height: 18 }}>
                      Review
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
