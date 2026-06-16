"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { MacSidebar } from "./Sidebar";
import { ToastContainer } from "@/components/ui/Toast";

const helpFAQ: [string, string][] = [
  ["workflow", "The AI workflow triages a case, retrieves relevant policy documents via RAG, runs investigation tools, and generates a structured recommendation for analyst review."],
  ["rag", "RAG (Retrieval-Augmented Generation) performs semantic search over the policy knowledge base and injects the most relevant policy chunks into the AI prompt — grounding recommendations in actual bank policy."],
  ["recommendation", "Each recommendation includes a multi-paragraph rationale, confidence score, supporting/concerning/missing evidence, structured decision metadata, and verbatim policy citations."],
  ["policy", "Policy documents live in the knowledge base. When a workflow runs, the most relevant policy sections are retrieved and quoted in the recommendation."],
  ["citation", "Policy citations include the exact document, section number, a verbatim quote, and an explanation of how the policy supports the recommendation."],
  ["approve", "Approving a case accepts the AI's recommended action. You must leave an analyst note before approving — it is recorded in the audit trail."],
  ["reject", "Rejecting a case declines the recommended action. Provide a rejection reason; it is stored in the audit trail."],
  ["escalate", "Escalating sends the case to a senior analyst or supervisor. Always add a note explaining why before escalating."],
  ["note", "Analyst notes are mandatory before any decision (approve, reject, escalate). Notes are permanently stored in the audit trail."],
  ["audit", "The audit trail records every action, status change, and note on a case for compliance and traceability."],
  ["badge", "Status and priority badges on the Dashboard are clickable — click one to jump to a filtered case list."],
  ["dashboard", "The dashboard shows total cases, average AI confidence, tool invocations, approval rate, and case breakdowns by status and priority."],
  ["metrics", "Metrics track system performance: case volume, AI confidence distribution, tool call latency, and analyst approval rate over time."],
  ["case", "Cases represent transaction exceptions. They flow through: created → triaged → awaiting review → approved / escalated / rejected → completed."],
  ["triage", "The Triage Agent classifies each case by issue type (duplicate charge, refund mismatch, settlement delay, etc.) and extracts key entities."],
  ["confidence", "Confidence scores reflect the AI's certainty in its recommendation. Below 0.70, the system recommends escalation rather than guessing."],
  ["seed", "Use the seed script to populate the database with sample cases and policies for the demo."],
];

function getHelpResponse(input: string): string {
  const lower = input.toLowerCase();
  for (const [kw, ans] of helpFAQ) {
    if (lower.includes(kw)) return ans;
  }
  return "I can answer questions about cases, workflows, RAG, recommendations, policy citations, analyst notes, audit trail, metrics, and the dashboard. What would you like to know?";
}

export function ClientLayout({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();

  // Auth guard
  const [checked, setChecked] = useState(false);

  // Sidebar (responsive default: closed on narrow)
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Menubar
  const [activeMenu, setActiveMenu] = useState<string | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // Sign-out modal
  const [signedOut, setSignedOut] = useState(false);

  // Help chatbot
  const [helpOpen, setHelpOpen] = useState(false);
  const [helpMessages, setHelpMessages] = useState<{ role: "user" | "assistant"; text: string }[]>([
    { role: "assistant", text: "Hi! I'm the LedgerDesk assistant. Ask me anything about cases, workflows, RAG, policies, analyst decisions, or the audit trail." },
  ]);
  const [helpInput, setHelpInput] = useState("");
  const helpEndRef  = useRef<HTMLDivElement>(null);
  const helpInputRef = useRef<HTMLInputElement>(null);

  /* ── Auth guard ──────────────────────────────────────────────── */
  useEffect(() => {
    if (pathname.startsWith("/login")) { setChecked(true); return; }
    const token = typeof window !== "undefined" ? localStorage.getItem("ld_token") : null;
    if (!token) {
      router.replace("/login");
    } else {
      setChecked(true);
    }
  }, [pathname, router]);

  /* ── Responsive sidebar: start collapsed on narrow viewports ─── */
  useLayoutEffect(() => {
    if (typeof window !== "undefined" && window.innerWidth < 640) {
      setSidebarOpen(false);
    }
  }, []);

  /* ── Close menu on outside click ────────────────────────────── */
  useEffect(() => {
    const h = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setActiveMenu(null);
      }
    };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  /* ── Scroll help chat to bottom ─────────────────────────────── */
  useEffect(() => {
    helpEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [helpMessages]);

  /* ── Sign-out handler (called by sidebar) ────────────────────── */
  const handleSignOut = () => {
    localStorage.removeItem("ld_token");
    localStorage.removeItem("ld_user");
    setSignedOut(true);
    setActiveMenu(null);
  };

  /* ── Help chatbot ────────────────────────────────────────────── */
  const handleHelpSend = () => {
    const text = helpInput.trim();
    if (!text) return;
    setHelpMessages(prev => [...prev, { role: "user", text }]);
    setHelpInput("");
    setTimeout(() => {
      setHelpMessages(prev => [...prev, { role: "assistant", text: getHelpResponse(text) }]);
    }, 280);
  };

  /* ── Menubar actions ─────────────────────────────────────────── */
  const navigation = [
    { name: "Dashboard",   href: "/" },
    { name: "Case Queue",  href: "/cases" },
    { name: "Escalations", href: "/escalations" },
    { name: "Policies",    href: "/policies" },
    { name: "Audit Trail", href: "/audit" },
    { name: "Metrics",     href: "/metrics" },
  ];

  const menus: Record<string, { label: string; action: () => void; separator?: boolean }[]> = {
    LedgerDesk: [
      ...navigation.map(n => ({ label: n.name, action: () => router.push(n.href) })),
      { label: "---separator---", action: () => {}, separator: true },
      { label: "Sign Out…", action: handleSignOut },
    ],
    File: [
      { label: "Print…", action: () => window.print() },
    ],
    View: [
      { label: "Full Screen",   action: () => { if (!document.fullscreenElement) document.documentElement.requestFullscreen(); else document.exitFullscreen(); } },
      { label: "Normal (100%)", action: () => { document.body.style.setProperty("zoom", "1"); } },
      { label: "Compact (90%)", action: () => { document.body.style.setProperty("zoom", "0.9"); } },
      { label: "Mini (80%)",    action: () => { document.body.style.setProperty("zoom", "0.8"); } },
      { label: "---separator---", action: () => {}, separator: true },
      { label: sidebarOpen ? "Hide Sidebar" : "Show Sidebar", action: () => setSidebarOpen(o => !o) },
    ],
    Help: [
      { label: "LedgerDesk Help…", action: () => { setHelpOpen(true); setActiveMenu(null); } },
    ],
  };

  if (!checked) return null;

  return (
    <div className="mac-window mac-window-full">
      {/* ── Title Bar ────────────────────────────────────────────── */}
      <div className="mac-titlebar">
        <span className="mac-widget" />
        <span className="mac-widget" />
        <span className="mac-widget" />
        <span className="mac-titlebar-title">LedgerDesk — Financial Operations</span>
      </div>

      {/* ── Menu Bar ─────────────────────────────────────────────── */}
      <div className="mac-menubar" ref={menuRef}>
        <span className="mac-menuitem" style={{ fontWeight: "bold", fontSize: 13 }}>&#63743;</span>

        {["LedgerDesk", "File", "View", "Help"].map(menu => (
          <div key={menu} style={{ position: "relative" }}>
            <span
              className={`mac-menuitem${activeMenu === menu ? " mac-menuitem-active" : ""}`}
              onClick={() => setActiveMenu(activeMenu === menu ? null : menu)}
            >
              {menu}
            </span>
            {activeMenu === menu && (
              <div style={{
                position: "absolute", top: "100%", left: 0, zIndex: 200,
                background: "#D4D0C8",
                border: "1px solid #000",
                boxShadow: "2px 2px 0 rgba(0,0,0,0.4)",
                minWidth: 168,
                paddingTop: 2, paddingBottom: 2,
              }}>
                {menus[menu]?.map((item, i) =>
                  item.separator ? (
                    <hr key={i} style={{ margin: "2px 0" }} />
                  ) : (
                    <div
                      key={item.label}
                      className="mac-dropdown-item"
                      onClick={() => { item.action(); setActiveMenu(null); }}
                    >
                      {item.label}
                    </div>
                  )
                )}
              </div>
            )}
          </div>
        ))}

        {/* Hamburger — visible on narrow screens via CSS */}
        <button
          className="mac-hamburger-btn"
          onClick={() => setSidebarOpen(o => !o)}
          title="Toggle sidebar"
        >
          ☰
        </button>
      </div>

      {/* ── Body: sidebar + content ──────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative" }}>
        {sidebarOpen && (
          <>
            {/* Overlay backdrop on narrow screens */}
            <div className="mac-sidebar-backdrop" onClick={() => setSidebarOpen(false)} />
            <MacSidebar onSignOut={handleSignOut} />
          </>
        )}
        <main className="mac-content" style={{ padding: 0 }}>
          <div style={{ padding: "12px" }}>{children}</div>
        </main>
      </div>

      {/* ── Status Bar ───────────────────────────────────────────── */}
      <div className="mac-statusbar">
        <span>LedgerDesk Operations Portal</span>
        <span style={{ marginLeft: "auto" }}>
          {new Date().toLocaleDateString("en-US", { weekday: "short", year: "numeric", month: "short", day: "numeric" })}
        </span>
        <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#006400", display: "inline-block" }} />
          Connected
        </span>
        <button
          onClick={() => { setHelpOpen(true); }}
          style={{
            background: "#000080", color: "#fff", border: "1px solid #000",
            boxShadow: "inset 1px 1px 0 #4444AA, inset -1px -1px 0 #000040",
            width: 16, height: 13, fontSize: 10, fontWeight: "bold",
            fontFamily: '"Chicago", sans-serif',
            display: "inline-flex", alignItems: "center", justifyContent: "center",
            cursor: "default", padding: 0, lineHeight: 1,
          }}
          title="Open Help"
        >
          ?
        </button>
      </div>

      {/* ── Toast notifications ────────────────────────────────── */}
      <ToastContainer />

      {/* ── Sign-out confirmation modal ───────────────────────────── */}
      {signedOut && (
        <div className="mac-modal-backdrop">
          <div className="mac-dialog" style={{ width: 320 }}>
            <div className="mac-dialog-titlebar">
              <span className="mac-widget" />
              <span style={{ flex: 1, textAlign: "center", fontFamily: '"Chicago","Charcoal",sans-serif', fontSize: 12, fontWeight: "bold" }}>
                LedgerDesk
              </span>
            </div>
            <div className="mac-dialog-body" style={{ textAlign: "center", padding: "24px 20px 16px" }}>
              <div style={{
                width: 44, height: 44, margin: "0 auto 14px",
                background: "#000080", border: "2px solid #000",
                boxShadow: "inset 1px 1px 0 #4444AA, inset -1px -1px 0 #000040",
                display: "flex", alignItems: "center", justifyContent: "center",
                fontFamily: '"Chicago",sans-serif', fontSize: 13, fontWeight: "bold", color: "#fff",
              }}>
                LD
              </div>
              <p style={{ fontFamily: '"Chicago","Charcoal",sans-serif', fontSize: 12, fontWeight: "bold", color: "#000", marginBottom: 6 }}>
                Signed out
              </p>
              <p style={{ fontFamily: '"Geneva",sans-serif', fontSize: 11, color: "#555" }}>
                Sign in to continue using LedgerDesk.
              </p>
            </div>
            <div className="mac-dialog-footer" style={{ justifyContent: "center" }}>
              <button
                className="mac-btn-default"
                onClick={() => { setSignedOut(false); router.replace("/login"); }}
              >
                Sign In
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Help chatbot ─────────────────────────────────────────── */}
      {helpOpen && (
        <div className="mac-modal-backdrop" onClick={(e) => { if (e.target === e.currentTarget) setHelpOpen(false); }}>
          <div className="mac-dialog" style={{ width: 420, height: 500, display: "flex", flexDirection: "column" }}>
            <div className="mac-dialog-titlebar">
              <span className="mac-widget" onClick={() => setHelpOpen(false)} />
              <span style={{ flex: 1, textAlign: "center", fontFamily: '"Chicago","Charcoal",sans-serif', fontSize: 12, fontWeight: "bold" }}>
                LedgerDesk Help
              </span>
            </div>
            {/* Messages */}
            <div style={{ flex: 1, overflowY: "auto", padding: "10px", display: "flex", flexDirection: "column", gap: 8, background: "#fff" }}>
              {helpMessages.map((msg, i) => (
                <div key={i} style={{ display: "flex", justifyContent: msg.role === "user" ? "flex-end" : "flex-start" }}>
                  <div style={{
                    maxWidth: "82%", padding: "6px 10px",
                    background: msg.role === "user" ? "#000080" : "#D4D0C8",
                    color:      msg.role === "user" ? "#fff"    : "#000",
                    border:    "1px solid " + (msg.role === "user" ? "#000040" : "#888"),
                    boxShadow: "inset 1px 1px 0 " + (msg.role === "user" ? "#4444AA" : "#fff") +
                               ", inset -1px -1px 0 " + (msg.role === "user" ? "#000040" : "#888"),
                    fontFamily: '"Geneva",sans-serif', fontSize: 11, lineHeight: 1.6,
                  }}>
                    {msg.text}
                  </div>
                </div>
              ))}
              <div ref={helpEndRef} />
            </div>
            {/* Input */}
            <div style={{
              padding: "8px 10px",
              borderTop: "1px solid #888",
              boxShadow: "inset 0 1px 0 #fff",
              background: "#D4D0C8",
              display: "flex", gap: 6,
            }}>
              <input
                ref={helpInputRef}
                type="text"
                value={helpInput}
                onChange={(e) => setHelpInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleHelpSend()}
                placeholder="Ask about cases, workflows, RAG, policies…"
                className="mac-input"
                style={{ flex: 1 }}
                autoFocus
              />
              <button onClick={handleHelpSend} className="mac-btn" style={{ minWidth: 0, padding: "2px 12px" }}>
                Send
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
