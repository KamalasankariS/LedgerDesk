"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface PolicyItem {
  id: string;
  title: string;
  category: string;
  version: string;
  content: string | null;
}

export default function PoliciesPage() {
  const [policies, setPolicies]         = useState<PolicyItem[]>([]);
  const [selected, setSelected]         = useState<PolicyItem | null>(null);
  const [loadingList, setLoadingList]   = useState(true);
  const [loadingContent, setLoadingContent] = useState(false);
  const [contentError, setContentError] = useState<string | null>(null);

  useEffect(() => {
    api.policies.list().then(setPolicies).catch(() => setPolicies([])).finally(() => setLoadingList(false));
  }, []);

  const handleSelect = async (policy: PolicyItem) => {
    setSelected({ ...policy, content: null });
    setContentError(null);
    setLoadingContent(true);
    try {
      const doc = await api.policies.get(policy.id);
      setSelected(doc);
    } catch (err: unknown) {
      setContentError(err instanceof Error ? err.message : "Failed to load policy content.");
    } finally {
      setLoadingContent(false);
    }
  };

  if (loadingList) {
    return (
      <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 8, height: "calc(100vh - 120px)" }}>
        <div className="card" />
        <div className="card" />
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 8, height: "calc(100vh - 120px)" }}>

      {/* Policy list */}
      <div className="card p-0" style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div className="card-header">
          <h3>Policy Documents</h3>
          <span style={{ fontFamily: '"Monaco", monospace', fontSize: 10, color: "#555" }}>{policies.length}</span>
        </div>
        <div style={{ overflowY: "auto", flex: 1 }}>
          {policies.length === 0 ? (
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#888", padding: "12px 10px" }}>
              No policies found. Seed the database.
            </p>
          ) : (
            policies.map((p) => {
              const isActive = selected?.id === p.id;
              return (
                <button
                  key={p.id}
                  onClick={() => handleSelect(p)}
                  style={{
                    display: "block", width: "100%", textAlign: "left",
                    padding: "5px 10px", borderBottom: "1px solid #D4D0C8",
                    background: isActive ? "#000080" : "transparent",
                    border: "none", cursor: "default",
                  }}
                >
                  <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: isActive ? "#fff" : "#000", fontWeight: isActive ? "bold" : "normal" }}>
                    {p.title}
                  </p>
                  <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: isActive ? "#ccc" : "#888" }}>
                    {p.category} · v{p.version}
                  </p>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Content viewer */}
      <div className="card p-0" style={{ overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {selected ? (
          <>
            <div className="card-header" style={{ flexShrink: 0 }}>
              <div>
                <h3 style={{ fontSize: 12 }}>{selected.title}</h3>
                <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>
                  {selected.category} · Version {selected.version}
                </span>
              </div>
              {loadingContent && <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#8B6914" }}>Loading…</span>}
            </div>
            <div style={{ overflowY: "auto", flex: 1, padding: "10px" }}>
              {contentError ? (
                <div style={{ background: "#FFE8E8", border: "1px solid #880000", color: "#880000", padding: "8px", fontSize: 11, fontFamily: '"Geneva", sans-serif' }}>
                  ⚠ {contentError}
                </div>
              ) : loadingContent ? (
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {[...Array(6)].map((_, i) => (
                    <div key={i} style={{ height: 10, background: "#D4D0C8", width: i % 3 === 2 ? "70%" : "100%" }} />
                  ))}
                </div>
              ) : selected.content ? (
                <pre style={{ fontFamily: '"Monaco", "Courier New", monospace', fontSize: 11, whiteSpace: "pre-wrap", lineHeight: 1.7, color: "#000", margin: 0 }}>
                  {selected.content}
                </pre>
              ) : (
                <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#888", fontStyle: "italic" }}>No content available.</p>
              )}
            </div>
          </>
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center", padding: 40 }}>
            <div style={{ width: 48, height: 48, background: "#D4D0C8", border: "1px solid #000", boxShadow: "inset 1px 1px 0 #fff, inset -1px -1px 0 #888", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24, marginBottom: 12 }}>
              ◻
            </div>
            <p style={{ fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold", color: "#000", marginBottom: 4 }}>
              Select a Policy
            </p>
            <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 11, color: "#555" }}>
              Choose a policy document from the list to view its full contents.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
