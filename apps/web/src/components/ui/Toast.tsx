"use client";

import { useEffect, useState } from "react";

interface ToastMessage {
  id: number;
  text: string;
  type: "error" | "success" | "info";
}

let toastId = 0;
let addToastFn: ((msg: Omit<ToastMessage, "id">) => void) | null = null;

export function showToast(text: string, type: "error" | "success" | "info" = "error") {
  addToastFn?.({ text, type });
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  useEffect(() => {
    addToastFn = (msg) => {
      const id = ++toastId;
      setToasts((prev) => [...prev, { ...msg, id }]);
      setTimeout(() => setToasts((prev) => prev.filter((t) => t.id !== id)), 4000);
    };
    return () => { addToastFn = null; };
  }, []);

  if (toasts.length === 0) return null;

  return (
    <div style={{ position: "fixed", bottom: 24, right: 16, zIndex: 999, display: "flex", flexDirection: "column", gap: 6 }}>
      {toasts.map((t) => (
        <div
          key={t.id}
          style={{
            background: t.type === "error" ? "#FFF0F0" : t.type === "success" ? "#F0FFF0" : "#E8E8FF",
            border: `1px solid ${t.type === "error" ? "#880000" : t.type === "success" ? "#006400" : "#000080"}`,
            boxShadow: "2px 2px 0 rgba(0,0,0,0.3), inset 1px 1px 0 #fff",
            padding: "6px 12px",
            maxWidth: 340,
            fontFamily: '"Geneva", sans-serif',
            fontSize: 11,
            color: t.type === "error" ? "#880000" : t.type === "success" ? "#006400" : "#000080",
            animation: "fadeIn 0.2s ease",
          }}
          onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}
