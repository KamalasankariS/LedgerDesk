"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const navigation = [
  { name: "Dashboard",   href: "/",            icon: "⊞" },
  { name: "Case Queue",  href: "/cases",        icon: "◻" },
  { name: "Escalations", href: "/escalations",  icon: "▲" },
  { name: "Policies",    href: "/policies",     icon: "⊟" },
  { name: "Audit Trail", href: "/audit",        icon: "☰" },
  { name: "Metrics",     href: "/metrics",      icon: "▦" },
  { name: "Evaluation", href: "/evaluation",   icon: "◈" },
  { name: "Prompts",    href: "/prompts",      icon: "¶" },
];

export function MacSidebar({ onSignOut }: { onSignOut?: () => void }) {
  const pathname = usePathname();

  const user = (() => {
    try {
      if (typeof window === "undefined") return null;
      const u = localStorage.getItem("ld_user");
      return u ? JSON.parse(u) : null;
    } catch { return null; }
  })();

  return (
    <aside className="mac-sidebar">
      {/* ── App header ─────────── */}
      <div className="mac-sidebar-header" style={{ fontSize: 11, letterSpacing: 0, textTransform: "none", fontWeight: "bold", color: "#000", padding: "5px 8px 4px" }}>
        LedgerDesk
      </div>

      {/* ── Section label ──────── */}
      <div className="mac-sidebar-header">Navigation</div>

      {/* ── Nav items ─────────── */}
      <nav style={{ flex: 1 }}>
        {navigation.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`mac-sidebar-item${isActive ? " mac-sidebar-item-active" : ""}`}
            >
              <span style={{ fontSize: 10, width: 14, textAlign: "center", flexShrink: 0 }}>
                {item.icon}
              </span>
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* ── User + sign-out ─────── */}
      <div className="mac-sidebar-header">Account</div>
      {user && (
        <div className="mac-sidebar-item" style={{ cursor: "default" }}>
          <span style={{ fontSize: 10, width: 14, textAlign: "center" }}>👤</span>
          <span style={{ overflow: "hidden", textOverflow: "ellipsis" }}>{user.full_name || user.email}</span>
        </div>
      )}
      <button
        onClick={onSignOut}
        className="mac-sidebar-item"
        style={{ width: "100%", background: "none", border: "none", textAlign: "left", cursor: "default", paddingLeft: 10 }}
      >
        <span style={{ fontSize: 10, width: 14, textAlign: "center", flexShrink: 0 }}>⏏</span>
        <span>Sign Out</span>
      </button>
    </aside>
  );
}

// Keep legacy export name for any remaining references
export { MacSidebar as Sidebar };
