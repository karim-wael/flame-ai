import type { Metadata } from "next";
import { Inter, Space_Grotesk } from "next/font/google";
import Shell from "@/components/Shell";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter", display: "swap" });
const grotesk = Space_Grotesk({ subsets: ["latin"], variable: "--font-grotesk", display: "swap" });

export const metadata: Metadata = {
  title: "FLARE AI — Space Fire Research Portal",
  description:
    "Explore fire and combustion experiments run in microgravity by NASA and JAXA, compare test conditions, and ask questions backed by sources. NASA Space Apps Challenge 2026.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`dark ${inter.variable} ${grotesk.variable}`}>
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200&display=block"
        />
      </head>
      <body className="font-body text-body-md antialiased">
        <Shell>{children}</Shell>
      </body>
    </html>
  );
}
