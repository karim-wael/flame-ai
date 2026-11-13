import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FLARE AI — Microgravity Combustion & Hybrid Knowledge Platform",
  description:
    "NASA Space Apps Challenge 2026 | Flame in Freefall — Research Explorer, Domain-Gated Similarity Engine, and Hybrid RAG Assistant.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#07090e] text-slate-100 antialiased selection:bg-orange-500/30">
        {children}
      </body>
    </html>
  );
}

