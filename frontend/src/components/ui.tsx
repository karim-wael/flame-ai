"use client";

import React, { useState } from "react";
import { DOMAIN_LABEL, GRAVITY_LABEL, missingText } from "@/lib/format";

export function Icon({ name, size = 20, className = "" }: { name: string; size?: number; className?: string }) {
  return (
    <span aria-hidden="true" className={`material-symbols-outlined ${className}`} style={{ fontSize: size }}>
      {name}
    </span>
  );
}

const DOMAIN_CHIP: Record<string, string> = {
  solid: "bg-primary-container/20 text-primary-container",
  gas: "bg-secondary/20 text-secondary",
  liquid_droplet: "bg-secondary/15 text-secondary",
  aerosol_smoke: "bg-surface-container-highest text-on-surface",
};

export function DomainChip({ domain }: { domain: string }) {
  return (
    <span className={`chip ${DOMAIN_CHIP[domain] ?? "bg-surface-container-high text-on-surface-variant"}`}>
      {DOMAIN_LABEL[domain] ?? domain}
    </span>
  );
}

export function GravityChip({ gravity }: { gravity: string }) {
  const earth = gravity === "normal_gravity";
  return (
    <span className={`chip ${earth ? "bg-tertiary-container/30 text-tertiary" : "bg-secondary/15 text-secondary"}`}>
      {GRAVITY_LABEL[gravity] ?? gravity}
    </span>
  );
}

/** A value that is absent in the source. Shown as a soft label, never as zero. */
export function NotRecorded({ reason, className = "" }: { reason?: string | null; className?: string }) {
  return (
    <span
      title={missingText(reason)}
      className={`inline-flex cursor-help items-center gap-1 rounded-full bg-surface-container-highest/70 px-2 py-0.5 font-display text-[11px] font-medium text-on-surface-variant/80 ${className}`}
    >
      Not recorded
      <Icon name="info" size={13} />
    </span>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: React.ReactNode;
  title: string;
  description: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex flex-col justify-between gap-space-md lg:flex-row lg:items-end">
      <div className="flex flex-col gap-space-xs">
        <div className="t-label flex flex-wrap items-center gap-space-sm tracking-widest">{eyebrow}</div>
        <h1 className="t-headline-lg text-on-surface">{title}</h1>
        <p className="t-body max-w-3xl text-on-surface-variant">{description}</p>
      </div>
      {children}
    </div>
  );
}

export function Loading({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" className="glass t-body flex items-center justify-center gap-space-sm p-space-xl text-on-surface-variant">
      <Icon name="progress_activity" className="animate-spin text-secondary" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="glass flex flex-col items-start gap-space-sm p-space-lg" style={{ border: "1px solid rgba(255,180,171,0.3)" }}>
      <div className="t-title flex items-center gap-space-sm text-error">
        <Icon name="cloud_off" />
        Something went wrong
      </div>
      <p className="t-body text-on-surface-variant">{message}</p>
      {onRetry && (
        <button type="button" onClick={onRetry} className="btn-ghost mt-space-xs">
          <Icon name="refresh" size={16} />
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ icon, title, children }: { icon: string; title: string; children?: React.ReactNode }) {
  return (
    <div className="glass flex flex-col items-center gap-space-sm p-space-2xl text-center">
      <Icon name={icon} size={36} className="text-secondary/70" />
      <div className="t-title text-on-surface">{title}</div>
      {children && <p className="t-body max-w-md text-on-surface-variant">{children}</p>}
    </div>
  );
}

export function Accordion({
  title,
  badge,
  hint,
  iconClass = "text-secondary",
  defaultOpen = false,
  children,
}: {
  title: string;
  badge?: React.ReactNode;
  hint?: string;
  iconClass?: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="overflow-hidden rounded-xl bg-surface-container-low/70 shadow-sm backdrop-blur-md">
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
        className="flex w-full items-center justify-between gap-space-md p-space-md text-left transition-colors hover:bg-surface-container"
      >
        <span className="flex flex-wrap items-center gap-space-sm">
          <Icon name="chevron_right" className={`${iconClass} transition-transform ${open ? "rotate-90" : ""}`} />
          <span className="t-title text-on-surface">{title}</span>
          {badge}
        </span>
        {hint && <span className="t-label hidden text-outline sm:inline">{hint}</span>}
      </button>
      {open && <div className="p-space-md pt-0">{children}</div>}
    </div>
  );
}

export function CopyButton({ text, label = "Copy" }: { text: string; label?: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          setTimeout(() => setCopied(false), 1500);
        } catch {
          /* clipboard unavailable */
        }
      }}
      className="t-code inline-flex items-center gap-1.5 rounded-lg bg-surface-container-high/80 px-space-md py-1.5 text-on-surface-variant transition-colors hover:bg-surface-container-highest hover:text-on-surface"
    >
      <Icon name={copied ? "check" : "content_copy"} size={16} />
      {copied ? "Copied" : label}
    </button>
  );
}

export function Select({
  label,
  value,
  onChange,
  children,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div className="relative min-w-[9.5rem] flex-1">
      <select
        aria-label={label}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full cursor-pointer appearance-none rounded-lg bg-surface-container-high/60 px-space-md py-2.5 pr-9 font-display text-[14px] font-semibold text-on-surface outline-none transition-colors hover:bg-surface-container-high"
      >
        {children}
      </select>
      <Icon name="expand_more" size={18} className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-on-surface-variant" />
    </div>
  );
}
