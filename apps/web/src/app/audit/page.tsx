"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { EmptyState } from "@/components/ui/EmptyState";
import type { AuditEvent } from "@/types";

export default function AuditPage() {
  const [events, setEvents]   = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter]   = useState<"all" | "human" | "system">("all");

  useEffect(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filter !== "all") params.actor_type = filter;
    api.audit.list(params)
      .then((data) => setEvents(data.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, [filter]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mac-toolbar">
        {(["all", "human", "system"] as const).map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={filter === f ? "mac-btn-default" : "mac-btn"}
            style={{ minWidth: 0, padding: "2px 10px", margin: filter === f ? 3 : 0 }}
          >
            {f === "all" ? "All Events" : f === "human" ? "Human" : "System"}
          </button>
        ))}
        <span style={{ marginLeft: "auto", fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#555" }}>
          {events.length} events
        </span>
      </div>

      {loading ? (
        <div className="card" style={{ height: 300 }} />
      ) : events.length === 0 ? (
        <EmptyState title="No audit events" description="Events will appear as cases are processed." />
      ) : (
        <div className="card p-0" style={{ overflow: "hidden" }}>
          <table className="mac-list" style={{ width: "100%" }}>
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Actor</th>
                <th>Event Type</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {events.map((e) => (
                <tr key={e.id}>
                  <td><span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555", whiteSpace: "nowrap" }}>{new Date(e.created_at).toLocaleString()}</span></td>
                  <td>
                    <span className={`badge ${e.actor_type === "system" ? "badge-blue" : "badge-green"}`}>
                      {e.actor_type}
                    </span>
                  </td>
                  <td><span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#333" }}>{e.event_type}</span></td>
                  <td style={{ fontSize: 11 }}>{e.action}</td>
                  <td><span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555" }}>{e.resource_type}</span></td>
                  <td style={{ fontSize: 10, color: "#555", maxWidth: 200, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                    {e.details ? JSON.stringify(e.details) : "—"}
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
