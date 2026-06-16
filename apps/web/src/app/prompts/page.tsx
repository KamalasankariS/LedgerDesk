"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface PromptVersionItem {
  id: string;
  agent_type: string;
  version: string;
  description: string | null;
  is_active: boolean;
  template_preview: string;
  created_at: string | null;
}

export default function PromptsPage() {
  const [grouped, setGrouped] = useState<Record<string, PromptVersionItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [expandedAgent, setExpandedAgent] = useState<string | null>(null);
  const [diffResult, setDiffResult] = useState<string | null>(null);
  const [diffLoading, setDiffLoading] = useState(false);
  const [fullTemplate, setFullTemplate] = useState<{ id: string; template: string } | null>(null);

  useEffect(() => {
    api.prompts
      .list()
      .then((data: Record<string, unknown>) => {
        const pv = (data as { prompt_versions: Record<string, PromptVersionItem[]> }).prompt_versions;
        setGrouped(pv || {});
      })
      .catch(() => setGrouped({}))
      .finally(() => setLoading(false));
  }, []);

  const handleDiff = async (a: string, b: string) => {
    setDiffLoading(true);
    try {
      const res = (await api.prompts.diff(a, b)) as { diff: string; has_changes: boolean };
      setDiffResult(res.diff || "No differences found.");
    } catch {
      setDiffResult("Failed to load diff.");
    }
    setDiffLoading(false);
  };

  const handleViewFull = async (id: string) => {
    if (fullTemplate?.id === id) {
      setFullTemplate(null);
      return;
    }
    try {
      const res = (await api.prompts.get(id)) as { id: string; template: string };
      setFullTemplate({ id: res.id, template: res.template });
    } catch {
      setFullTemplate(null);
    }
  };

  if (loading) return <div className="card" style={{ height: 300 }} />;

  const agentTypes = Object.keys(grouped);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div className="mac-toolbar">
        <span style={{ fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 12, fontWeight: "bold" }}>
          Prompt Versions
        </span>
        <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>
          {agentTypes.length} agent types
        </span>
      </div>

      {agentTypes.map((agentType) => {
        const versions = grouped[agentType];
        const isExpanded = expandedAgent === agentType;
        const active = versions.find((v) => v.is_active);

        return (
          <div key={agentType} className="card" style={{ padding: 0 }}>
            <div
              className="card-header"
              style={{ cursor: "pointer", justifyContent: "space-between" }}
              onClick={() => setExpandedAgent(isExpanded ? null : agentType)}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#000080" }}>
                  {isExpanded ? "v" : ">"}
                </span>
                <h3>{agentType.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}</h3>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                {active && (
                  <span className="badge badge-approved">Active: v{active.version}</span>
                )}
                <span style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555" }}>
                  {versions.length} version{versions.length !== 1 ? "s" : ""}
                </span>
              </div>
            </div>

            {isExpanded && (
              <div style={{ padding: "0" }}>
                {versions.map((v, i) => (
                  <div
                    key={v.id}
                    style={{
                      padding: "8px 10px",
                      borderBottom: i < versions.length - 1 ? "1px solid #D4D0C8" : "none",
                      background: v.is_active ? "#F0F0FF" : "transparent",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                        <span style={{ fontFamily: '"Monaco", monospace', fontSize: 12, fontWeight: "bold", color: "#000080" }}>
                          v{v.version}
                        </span>
                        {v.is_active && <span className="badge badge-approved">Active</span>}
                      </div>
                      <div style={{ display: "flex", gap: 4 }}>
                        <button
                          className="mac-btn"
                          style={{ minWidth: 0, padding: "1px 6px", fontSize: 10 }}
                          onClick={() => handleViewFull(v.id)}
                        >
                          {fullTemplate?.id === v.id ? "Hide" : "View Full"}
                        </button>
                        {i < versions.length - 1 && (
                          <button
                            className="mac-btn"
                            style={{ minWidth: 0, padding: "1px 6px", fontSize: 10 }}
                            onClick={() => handleDiff(versions[i + 1].id, v.id)}
                            disabled={diffLoading}
                          >
                            Diff with v{versions[i + 1].version}
                          </button>
                        )}
                      </div>
                    </div>
                    {v.description && (
                      <p style={{ fontFamily: '"Geneva", sans-serif', fontSize: 10, color: "#555", marginBottom: 4 }}>
                        {v.description}
                      </p>
                    )}
                    <div className="mac-inset" style={{ padding: 6, fontSize: 10 }}>
                      <pre style={{ fontFamily: '"Monaco", monospace', fontSize: 10, whiteSpace: "pre-wrap", color: "#333", margin: 0 }}>
                        {fullTemplate?.id === v.id ? fullTemplate.template : v.template_preview}
                      </pre>
                    </div>
                    {v.created_at && (
                      <p style={{ fontFamily: '"Monaco", monospace', fontSize: 9, color: "#888", marginTop: 4 }}>
                        Created: {new Date(v.created_at).toLocaleString()}
                      </p>
                    )}
                  </div>
                ))}

                {/* Compare panel */}
                {versions.length >= 2 && (
                  <div style={{ padding: "8px 10px", borderTop: "1px solid #D4D0C8" }}>
                    <button
                      className="mac-btn-default"
                      style={{ fontSize: 10, padding: "2px 10px" }}
                      onClick={() => handleDiff(versions[versions.length - 1].id, versions[0].id)}
                      disabled={diffLoading}
                    >
                      {diffLoading ? "Loading..." : `Compare v${versions[versions.length - 1].version} -> v${versions[0].version}`}
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* Diff Viewer */}
      {diffResult && (
        <div className="card" style={{ padding: 0 }}>
          <div className="card-header" style={{ justifyContent: "space-between" }}>
            <h3>Diff View</h3>
            <button
              className="mac-btn"
              style={{ minWidth: 0, padding: "1px 8px", fontSize: 10 }}
              onClick={() => setDiffResult(null)}
            >
              Close
            </button>
          </div>
          <div style={{ padding: 10, background: "#1E1E1E", overflowX: "auto" }}>
            <pre style={{ fontFamily: '"Monaco", monospace', fontSize: 10, margin: 0, lineHeight: 1.6 }}>
              {diffResult.split("\n").map((line, i) => {
                let color = "#D4D4D4";
                if (line.startsWith("+") && !line.startsWith("+++")) color = "#4EC9B0";
                else if (line.startsWith("-") && !line.startsWith("---")) color = "#F44747";
                else if (line.startsWith("@@")) color = "#569CD6";
                else if (line.startsWith("---") || line.startsWith("+++")) color = "#808080";
                return (
                  <div key={i} style={{ color, minHeight: 14 }}>
                    {line || " "}
                  </div>
                );
              })}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
