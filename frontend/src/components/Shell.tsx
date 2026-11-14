"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import React, { createContext, useContext } from "react";
import { api } from "@/lib/api";
import { useAsync } from "@/lib/hooks";
import { Health } from "@/lib/types";
import { ProvenanceProvider } from "./ProvenancePanel";
import { Icon } from "./ui";

const NAV = [
  { href: "/explorer", label: "Explorer", icon: "travel_explore" },
  { href: "/compare", label: "Compare", icon: "compare_arrows" },
  { href: "/assistant", label: "Assistant", icon: "smart_toy" },
  { href: "/data-sources", label: "Data Sources", icon: "dataset" },
];

interface HealthState {
  health: Health | null;
  offline: boolean;
  refresh: () => void;
}

const HealthContext = createContext<HealthState>({ health: null, offline: false, refresh: () => {} });
export const useHealth = () => useContext(HealthContext);

function Logo() {
  return (
    <svg viewBox="0 0 32 32" className="h-8 w-8 shrink-0" aria-hidden="true">
      <defs>
        <linearGradient id="flareLogo" x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor="#ff6b35" />
          <stop offset="60%" stopColor="#fbbf24" />
          <stop offset="100%" stopColor="#fde047" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="17" r="12" fill="none" stroke="#7bd0ff" strokeOpacity="0.35" strokeWidth="1.2" />
      <path d="M16 4c1.5 5 7 7.5 7 14a7 7 0 0 1-14 0c0-3 1.4-4.8 2.8-6.4.5 2 1.4 3 2.6 3.6C13.6 11 14.6 7.4 16 4z" fill="url(#flareLogo)" />
      <circle cx="16" cy="19.5" r="2.6" fill="#fff7d6" />
    </svg>
  );
}

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { data: health, error, reload } = useAsync(() => api.health(), []);
  const current = NAV.find((n) => pathname.startsWith(n.href));

  return (
    <HealthContext.Provider value={{ health, offline: !!error, refresh: reload }}>
      <ProvenanceProvider>
        {/* Ambient starburst glow behind the content */}
        <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
          <div className="absolute left-[56%] top-[40%] h-[720px] w-[720px] -translate-x-1/2 -translate-y-1/2 bg-[radial-gradient(circle,rgba(251,191,36,0.18)_0%,rgba(245,158,11,0.1)_30%,rgba(234,88,12,0.04)_55%,transparent_72%)] blur-2xl" />
          <div className="absolute left-[56%] top-[40%] h-[50px] w-[900px] -translate-x-1/2 -translate-y-1/2 rotate-[28deg] bg-gradient-to-r from-transparent via-amber-glow/15 to-transparent blur-lg" />
          <div className="absolute left-[56%] top-[40%] h-[50px] w-[900px] -translate-x-1/2 -translate-y-1/2 -rotate-[35deg] bg-gradient-to-r from-transparent via-amber-deep/15 to-transparent blur-lg" />
          <div className="absolute inset-0 opacity-[0.035]" style={{ backgroundImage: "radial-gradient(#fff 1px, transparent 1px)", backgroundSize: "24px 24px" }} />
        </div>

        {/* Sidebar (desktop) */}
        <aside
          className="fixed left-0 top-0 z-40 hidden h-full w-72 flex-col justify-between p-space-lg backdrop-blur-2xl lg:flex"
          style={{ background: "rgba(8, 14, 32, 0.86)", borderRight: "1px solid rgba(123, 208, 255, 0.12)" }}
        >
          <div className="flex flex-col gap-space-xl">
            <Link href="/explorer" className="flex items-center gap-space-md">
              <Logo />
              <span className="flex flex-col">
                <span className="t-headline-md leading-none tracking-tight text-primary">FLARE AI</span>
                <span className="t-label mt-space-xs tracking-wider text-secondary">NASA Space Apps Cairo</span>
              </span>
            </Link>
            <nav aria-label="Main" className="flex flex-col gap-space-xs">
              {NAV.map((item) => {
                const active = pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    aria-current={active ? "page" : undefined}
                    className={`t-title flex items-center gap-space-md rounded-lg px-space-md py-space-sm transition-colors ${
                      active
                        ? "bg-gradient-to-r from-amber-deep via-amber-glow to-amber-light font-bold text-amber-ink shadow-[0_0_18px_rgba(251,191,36,0.35)]"
                        : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                    }`}
                  >
                    <Icon name={item.icon} />
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          <div className="flex flex-col gap-space-md">
            <div className="t-code flex items-center justify-between px-space-xs text-on-surface-variant">
              <span>{health ? `API v${health.version}` : error ? "API offline" : "Connecting…"}</span>
              <span className={`inline-block h-2 w-2 rounded-full ${error ? "bg-error" : "animate-pulse bg-secondary"}`} />
            </div>
          </div>
        </aside>

        <div className="relative z-10 lg:pl-72">
          {/* Top bar */}
          <header
            className="fixed left-0 right-0 top-0 z-30 h-16 backdrop-blur-xl lg:left-72"
            style={{ background: "rgba(7, 11, 25, 0.8)", borderBottom: "1px solid rgba(123, 208, 255, 0.12)" }}
          >
            <div className="flex h-16 items-center justify-between gap-space-md px-space-md md:px-space-xl">
              <div className="flex min-w-0 items-center gap-space-sm">
                <span className="lg:hidden">
                  <Logo />
                </span>
                <span className="t-label hidden rounded-full bg-surface-container-high px-space-sm py-0.5 tracking-wider text-secondary sm:inline">
                  Space Apps Cairo 2026
                </span>
                <span className="t-label hidden text-outline-variant sm:inline">/</span>
                <span className="t-label truncate tracking-wider text-on-surface-variant">{current?.label ?? "FLARE AI"}</span>
              </div>
              <div className="t-code flex items-center gap-space-sm rounded-full bg-surface-container-low px-space-md py-space-xs text-on-surface-variant">
                <span className={`inline-block h-2 w-2 rounded-full ${error ? "bg-error" : health ? "bg-secondary" : "animate-pulse bg-tertiary"}`} />
                {error
                  ? "BACKEND OFFLINE"
                  : health
                    ? `${health.counts.investigations} STUDIES · ${health.counts.experiment_runs} TEST RUNS`
                    : "CONNECTING…"}
              </div>
            </div>
          </header>

          <main className="min-h-screen w-full pb-24 pt-16 lg:pb-0">
            <div className="mx-auto flex w-full max-w-[1720px] flex-col gap-space-xl p-space-md md:p-space-xl">{children}</div>
          </main>
        </div>

        {/* Bottom navigation (mobile / tablet) */}
        <nav
          aria-label="Main"
          className="fixed bottom-0 left-0 right-0 z-40 grid grid-cols-4 backdrop-blur-2xl lg:hidden"
          style={{ background: "rgba(8, 14, 32, 0.94)", borderTop: "1px solid rgba(123, 208, 255, 0.12)" }}
        >
          {NAV.map((item) => {
            const active = pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={`flex flex-col items-center gap-0.5 py-2.5 font-display text-[11px] font-semibold ${active ? "text-amber-glow" : "text-on-surface-variant"}`}
              >
                <Icon name={item.icon} />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </ProvenanceProvider>
    </HealthContext.Provider>
  );
}
