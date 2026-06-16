"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail]       = useState("");
  const [password, setPassword] = useState("");
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const res = await fetch("/api/v1/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "Invalid credentials");
      }
      const data = await res.json();
      localStorage.setItem("ld_token", data.access_token);
      localStorage.setItem("ld_user", JSON.stringify({ full_name: data.full_name, role: data.role, email: data.email }));
      router.push("/");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mac-desktop" style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
      {/* Mac OS 9 Dialog window */}
      <div className="mac-dialog" style={{ width: 340 }}>
        {/* Title bar */}
        <div className="mac-dialog-titlebar">
          <span className="mac-widget" />
          <span style={{
            flex: 1, textAlign: "center",
            fontFamily: '"Chicago", "Charcoal", "Geneva", sans-serif',
            fontSize: 12, fontWeight: "bold", color: "#000",
          }}>
            LedgerDesk — Sign In
          </span>
        </div>

        {/* Body */}
        <div className="mac-dialog-body">
          {/* App icon row */}
          <div style={{ textAlign: "center", marginBottom: 14 }}>
            <div style={{
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              width: 48, height: 48, background: "#000080", border: "2px solid #000",
              boxShadow: "inset 1px 1px 0 #4444AA, inset -1px -1px 0 #000040",
              fontFamily: '"Chicago", sans-serif', fontSize: 14, fontWeight: "bold", color: "#fff",
            }}>
              LD
            </div>
            <p style={{ marginTop: 6, fontFamily: '"Chicago", "Charcoal", sans-serif', fontSize: 11, fontWeight: "bold", color: "#000" }}>
              Operations Portal
            </p>
          </div>

          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: 10 }}>
              <label className="mac-label">Email Address</label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@yourbank.com"
                className="mac-input"
              />
            </div>

            <div style={{ marginBottom: 14 }}>
              <label className="mac-label">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="mac-input"
              />
            </div>

            {error && (
              <div style={{
                background: "#FFE8E8", border: "1px solid #CC0000", color: "#880000",
                padding: "4px 8px", fontSize: 11, marginBottom: 12,
                fontFamily: '"Geneva", sans-serif',
              }}>
                ⚠ {error}
              </div>
            )}

            <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
              <button
                type="submit"
                disabled={loading}
                className="mac-btn-default"
              >
                {loading ? "Signing in…" : "Sign In"}
              </button>
            </div>
          </form>

          <hr style={{ margin: "12px 0" }} />
          <p style={{ fontSize: 10, color: "#555", fontFamily: '"Geneva", sans-serif', textAlign: "center" }}>
            Demo: analyst@ledgerdesk.dev / demo123
          </p>
          <p style={{ fontSize: 10, color: "#555", fontFamily: '"Geneva", sans-serif', textAlign: "center", marginTop: 4 }}>
            Admin?{" "}
            <a href="http://localhost:3001" style={{ color: "#000080", textDecoration: "underline" }}>
              Open Admin Console
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
