"use client";

import React, { useMemo, useState } from "react";
import { useProvenance } from "@/components/ProvenancePanel";
import { useHealth } from "@/components/Shell";
import { DomainChip, ErrorState, GravityChip, Icon, Loading, PageHeader } from "@/components/ui";
import { api } from "@/lib/api";
import { fieldLabel } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import { DataSourceItem, IngestionReport } from "@/lib/types";

const SOURCE_STYLE: Record<string, { icon: string; bar: string }> = {
  "NASA PSI": { icon: "rocket_launch", bar: "from-secondary-container to-secondary" },
  "JAXA DARTS": { icon: "hub", bar: "from-secondary to-primary-container" },
  "UL FSRI": { icon: "local_fire_department", bar: "from-tertiary to-primary-container" },
};

const COUNT_LABELS: Record<string, string> = {
  data_sources: "Sources",
  investigations: "Studies",
  source_files: "Files",
  experiment_runs: "Test runs",
  measurements: "Measurements",
  explicit_missing_measurements: "Values marked not recorded",
  field_mappings: "Unit conversions",
  derived_results: "Calculated values",
  knowledge_documents: "Documents",
  knowledge_chunks: "Passages",
};

export default function DataSourcesPage() {
  const { health, refresh: refreshHealth } = useHealth();
  const openProvenance = useProvenance();
  const sources = useAsync(() => api.sources(), []);
  const studies = useAsync(() => api.investigations(), []);
  const [report, setReport] = useState<IngestionReport | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const runsByPublisher = useMemo(() => {
    const map: Record<string, number> = {};
    (studies.data ?? []).forEach((s) => (map[s.publisher] = (map[s.publisher] ?? 0) + s.run_count));
    return map;
  }, [studies.data]);

  const accessDate = sources.data?.[0]?.access_date;

  const refreshData = async () => {
    setRefreshing(true);
    setRefreshError(null);
    try {
      setReport(await api.ingest());
      sources.reload();
      studies.reload();
      refreshHealth();
    } catch (e) {
      setRefreshError(e instanceof Error ? e.message : "The refresh failed.");
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-space-xl">
      <PageHeader
        eyebrow={
          <>
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-secondary-container" />
            <span className="text-secondary">Where the data comes from</span>
          </>
        }
        title="Data Sources & Unit Conversions"
        description="The organisations behind the data in FLARE AI, how many studies and test runs each one provides, and how their units were converted to a common standard."
      >
        <div className="flex flex-col items-start gap-space-md sm:flex-row sm:items-center">
          {accessDate && (
            <div className="flex flex-col sm:text-right">
              <span className="t-label tracking-wider text-outline">Sources accessed</span>
              <span className="t-code text-primary">{accessDate}</span>
            </div>
          )}
          <button type="button" onClick={refreshData} disabled={refreshing} className="btn-amber">
            <Icon name="sync" size={18} className={refreshing ? "animate-spin" : ""} />
            {refreshing ? "Refreshing…" : "Refresh data"}
          </button>
        </div>
      </PageHeader>

      {refreshError && <ErrorState message={refreshError} onRetry={refreshData} />}

      {report && (
        <div className="glass flex flex-col gap-space-md p-space-lg" style={{ border: "1px solid rgba(123, 208, 255, 0.25)" }}>
          <div className="flex items-center justify-between gap-space-md">
            <div className="t-title flex items-center gap-space-sm text-secondary">
              <Icon name="check_circle" />
              Data reloaded from the source files
            </div>
            <button type="button" aria-label="Dismiss" onClick={() => setReport(null)} className="text-on-surface-variant hover:text-on-surface">
              <Icon name="close" size={18} />
            </button>
          </div>
          <div className="grid grid-cols-2 gap-space-sm sm:grid-cols-5">
            {Object.entries(report.counts).map(([k, v]) => (
              <div key={k} className="tile flex flex-col p-space-sm">
                <span className="t-label tracking-wider text-on-surface-variant">{COUNT_LABELS[k] ?? k.replace(/_/g, " ")}</span>
                <span className="t-title text-on-surface">{v}</span>
              </div>
            ))}
          </div>
          <ul className="t-code flex flex-col gap-1 text-on-surface-variant">
            {report.audit_log.map((line) => (
              <li key={line} className="flex gap-1.5">
                <Icon name="chevron_right" size={14} className="mt-0.5 shrink-0 text-secondary" />
                {line}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary numbers (live from the API) */}
      <div className="grid grid-cols-2 gap-space-md sm:grid-cols-4">
        <Bento label="Test runs" icon="local_fire_department" value={health?.counts.experiment_runs} tone="text-on-surface" note={`${health?.counts.measurements ?? "—"} measurements`} />
        <Bento label="Studies" icon="science" value={health?.counts.investigations} tone="text-secondary" note={`from ${health?.counts.data_sources ?? "—"} organisations`} />
        <Bento label="Unit conversions" icon="balance" value={health?.counts.field_mappings} tone="text-tertiary" note="Mapped to common units" />
        <Bento label="Source files" icon="fingerprint" value={health?.counts.source_files} tone="text-primary-container" note="Each with a SHA-256 fingerprint" />
      </div>

      {sources.error ? (
        <ErrorState message={sources.error} onRetry={sources.reload} />
      ) : !sources.data ? (
        <Loading label="Loading sources…" />
      ) : (
        <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-3">
          {sources.data.map((src) => (
            <SourceCard key={src.id} src={src} runs={runsByPublisher[src.publisher]} />
          ))}
        </div>
      )}

      {/* Registered studies: every row opens the source-details panel */}
      <div className="glass-strong flex flex-col gap-space-md p-space-lg">
        <div className="flex flex-col items-start justify-between gap-space-sm border-b border-white/5 pb-space-sm md:flex-row md:items-center">
          <div className="flex items-center gap-space-sm">
            <Icon name="verified_user" className="text-primary-container" />
            <h2 className="t-headline-md text-on-surface">Trace a study to its source</h2>
          </div>
          <span className="t-code text-on-surface-variant">Select a study to see its files, fingerprints and DOI</span>
        </div>
        {studies.error ? (
          <ErrorState message={studies.error} onRetry={studies.reload} />
        ) : !studies.data ? (
          <Loading label="Loading studies…" />
        ) : (
          <div className="flex flex-col gap-space-xs">
            {studies.data.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => openProvenance(s.external_id)}
                className="tile flex flex-col gap-space-sm p-space-md text-left transition-colors hover:bg-surface-container-high md:flex-row md:items-center md:justify-between"
              >
                <span className="flex min-w-0 items-center gap-space-md">
                  <span className="t-code shrink-0 rounded bg-surface-container-high px-space-sm py-0.5 font-bold text-secondary">{s.external_id}</span>
                  <span className="flex min-w-0 flex-col">
                    <span className="t-body truncate font-medium text-on-surface">{s.title}</span>
                    <span className="t-code text-outline">
                      {s.publisher} · {s.doi ? `DOI ${s.doi}` : "No DOI listed"}
                    </span>
                  </span>
                </span>
                <span className="flex shrink-0 items-center gap-space-sm">
                  <GravityChip gravity={s.gravity_regime} />
                  <DomainChip domain={s.combustion_domain} />
                  <span className="t-code text-on-surface-variant">
                    {s.file_count} {s.file_count === 1 ? "file" : "files"}
                  </span>
                  <Icon name="chevron_right" className="text-secondary" />
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function Bento({ label, icon, value, tone, note }: { label: string; icon: string; value?: number; tone: string; note: string }) {
  return (
    <div className="flex flex-col gap-space-xs rounded-xl border border-white/5 bg-surface-container-low/70 p-space-lg shadow-lg backdrop-blur-md">
      <div className="flex items-center justify-between">
        <span className="t-label tracking-wider text-on-surface-variant">{label}</span>
        <Icon name={icon} size={18} className="text-secondary" />
      </div>
      <span className={`t-headline-lg font-bold ${tone}`}>{value ?? "—"}</span>
      <span className="t-code text-outline">{note}</span>
    </div>
  );
}

function SourceCard({ src, runs }: { src: DataSourceItem; runs?: number }) {
  const [open, setOpen] = useState(false);
  const earth = src.domain_track === "terrestrial_baseline";
  const style = SOURCE_STYLE[src.publisher] ?? { icon: "dataset", bar: "from-secondary-container to-secondary" };
  const accent = earth ? "text-tertiary" : "text-secondary";

  return (
    <div className="relative flex flex-col gap-space-md overflow-hidden rounded-xl border border-white/5 bg-surface-container-low/80 p-space-lg shadow-xl backdrop-blur-md">
      <div className={`absolute left-0 top-0 h-1 w-full bg-gradient-to-r ${style.bar}`} />
      <div className="flex items-start justify-between gap-space-sm">
        <div className="flex items-center gap-space-md">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-surface-container-high shadow-inner ${accent}`}>
            <Icon name={style.icon} size={24} />
          </div>
          <h3 className="t-headline-md tracking-tight text-on-surface">{src.publisher}</h3>
        </div>
        <span className={`chip shrink-0 border px-space-sm py-1 ${earth ? "border-tertiary/20 bg-tertiary/15 text-tertiary" : "border-secondary/20 bg-secondary/10 text-secondary"}`}>
          {earth ? "Earth reference" : "Space data"}
        </span>
      </div>
      <p className="t-body leading-relaxed text-on-surface-variant">{src.source_name}</p>

      <div className="grid grid-cols-2 gap-space-sm rounded-lg border border-white/5 bg-surface-container/60 p-space-sm">
        <div>
          <span className="t-label block text-outline">Test runs</span>
          <span className={`t-title font-bold ${earth ? "text-tertiary" : "text-primary"}`}>{runs ?? "—"}</span>
        </div>
        <div>
          <span className="t-label block text-outline">Studies</span>
          <span className="t-title font-bold text-secondary">{src.investigation_count}</span>
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-white/5 bg-surface-container/40">
        <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full items-center justify-between px-space-md py-space-sm text-left transition-colors hover:bg-surface-container-high/30">
          <span className="flex items-center gap-space-xs font-display text-[14px] font-semibold text-primary">
            <Icon name="tune" size={16} />
            How we converted units ({src.field_mappings.length})
          </span>
          <Icon name="expand_more" className={`text-outline transition-transform duration-200 ${open ? "rotate-180" : ""}`} />
        </button>
        {open && (
          <div className="t-code flex flex-col px-space-md pb-space-md pt-space-xs text-on-surface-variant">
            {src.field_mappings.length === 0 && <span>No conversions were needed.</span>}
            {src.field_mappings.map((fm) => (
              <div key={fm.id} className="flex flex-col gap-0.5 border-b border-white/5 py-1.5 last:border-b-0">
                <div className="flex items-center justify-between gap-space-sm">
                  <span className="text-on-surface">{fieldLabel(fm.canonical_field)}</span>
                  <span className={accent}>
                    {fm.source_unit} → {fm.canonical_unit}
                  </span>
                </div>
                <span className="text-outline">{fm.transform_description}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <p className="t-code text-outline">Licence: {src.license}</p>

      <a
        href={src.source_url}
        target="_blank"
        rel="noreferrer"
        className="mt-auto inline-flex items-center justify-between rounded-lg px-space-md py-space-sm font-display text-[14px] font-semibold text-amber-light transition-colors hover:brightness-125"
        style={{ border: "1px solid rgba(251, 191, 36, 0.4)", background: "rgba(245, 158, 11, 0.08)" }}
      >
        Visit {src.publisher}
        <Icon name="north_east" size={18} />
      </a>
    </div>
  );
}
