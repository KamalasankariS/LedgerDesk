import type { Metadata } from "next";
import "@/styles/globals.css";
import { ClientLayout } from "@/components/layout/ClientLayout";

export const metadata: Metadata = {
  title: {
    default: "LedgerDesk",
    template: "%s — LedgerDesk",
  },
  description: "Agentic financial operations copilot for transaction exception handling",
  icons: { icon: "/favicon.svg" },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="mac-desktop" style={{ display: "flex", alignItems: "stretch", justifyContent: "stretch", minHeight: "100vh" }}>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}
