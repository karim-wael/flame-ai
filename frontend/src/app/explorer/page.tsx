"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useProvenance } from "@/components/ProvenancePanel";
import ScatterChart, { ChartPoint } from "@/components/ScatterChart";
import { Accordion, DomainChip, EmptyState, ErrorState, GravityChip, Icon, Loading, NotRecorded, PageHeader, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { bytes, DOMAIN_LABEL, fieldLabel, num, OUTCOME_BY_DOMAIN, pct, shortHash, yearWindow } from "@/lib/format";
import { useAsync, useDebounced } from "@/lib/hooks";
import { ExperimentRun, InvestigationDetail, InvestigationSummary, Measurement } from "@/lib/types";

export default function ExplorerPage() {
  const [search, setSearch] = useState("");
  const [source, setSource] = useState("");
  const [domain, setDomain] = useState("");
  const [gravity, setGravity] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const debouncedSearch = useDebounced(search);

  const all = useAsync(() => api.investigations(), []);
  const list = useAsync(
    () => api.investigations({ source, domain, gravity, search: debouncedSearch }),
    [source, domain, gravity, debouncedSearch],
  );

  // Keep a valid selection as the filtered list changes.
  useEffect(() => {
    if (!list.data) return;
    if (!list.data.some((i) => i.external_id === selectedId)) {
      setSelectedId(list.data[0]?.external_id ?? null);
    }
  }, [list.data, selectedId]);

  const totals = useMemo(() => {
    const items = all.data ?? [];
    return {
      total: items.length,
      space: items.filter((i) => i.gravity_regime === "microgravity").length,
      earth: items.filter((i) => i.gravity_regime === "normal_gravity").length,
    };
  }, [all.data]);

  const hasFilters = !!(search || source || domain || gravity);
  const reset = () => {
    setSearch("");
    setSource("");
    setDomain("");
    setGravity("");
  };

  return (
    <>
      <PageHeader
        eyebrow={
          <span className="inline-flex items-center gap-1.5 rounded-full bg-surface-container-high px-space-sm py-0.5 text-primary">
            <span className="h-1.5 w-1.5 rounded-full bg-primary-container" />
            Experiment catalogue
          </span>
        }
        title="Experiment Explorer"
        description="Browse the space-fire studies, open one, and look at its individual test runs: what burned, under which conditions, and what was measured."
      >
        <div className="glass grid grid-cols-3 gap-space-sm p-space-sm">
          <Metric label="Total studies" value={all.data ? totals.total : "—"} />
          <Metric label="Microgravity" value={all.data ? totals.space : "—"} tone="text-secondary" boxed />
          <Metric label="Earth 1g" value={all.data ? totals.earth : "—"} tone="text-tertiary" />
        </div>
      </PageHeader>

      {/* Filter bar */}
      <div className="glass flex flex-col items-stretch gap-space-md p-space-md xl:flex-row xl:items-center">
        <div className="group relative flex-1">
          <Icon name="search" className="absolute left-space-md top-1/2 -translate-y-1/2 text-on-surface-variant transition-colors group-focus-within:text-secondary" />
          <input
            type="text"
            aria-label="Search studies"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by study code, name, or platform…"
            className="field pl-11"
          />
        </div>
        <div className="flex flex-wrap items-center gap-space-sm">
          <Select label="Data source" value={source} onChange={setSource}>
            <option value="">All sources</option>
            <option value="NASA PSI">NASA PSI</option>
          </Select>
          <Select label="Fuel type" value={domain} onChange={setDomain}>
            <option value="">All fuels</option>
            <option value="solid">Solid fuel</option>
            <option value="gas">Gas flame</option>
            <option value="liquid_droplet">Liquid droplet</option>
            <option value="aerosol_smoke">Smoke</option>
          </Select>
          <Select label="Gravity" value={gravity} onChange={setGravity}>
            <option value="">All gravities</option>
            <option value="microgravity">Space (microgravity)</option>
            <option value="normal_gravity">Earth (1g)</option>
          </Select>
          <button
            type="button"
            onClick={reset}
            disabled={!hasFilters}
            title="Reset all filters"
            aria-label="Reset all filters"
            className="flex items-center justify-center rounded-lg bg-surface-container px-space-md py-2.5 text-on-surface-variant transition-colors hover:bg-surface-container-high hover:text-on-surface disabled:opacity-40"
          >
            <Icon name="restart_alt" size={18} />
          </button>
        </div>
      </div>

      {list.error ? (
        <ErrorState message={list.error} onRetry={list.reload} />
      ) : !list.data ? (
        <Loading label="Loading studies…" />
      ) : list.data.length === 0 ? (
        <EmptyState icon="search_off" title="No studies match these filters">
          Try a different search term or reset the filters to see every study.
        </EmptyState>
      ) : (
        <div className="grid grid-cols-1 items-start gap-space-lg lg:grid-cols-12">
          <div className="flex flex-col gap-space-md lg:col-span-5">
            <div className="t-label flex items-center gap-1.5 px-space-xs tracking-wider text-on-surface-variant">
              <Icon name="science" size={16} className="text-secondary" />
              Studies ({list.data.length}
              {hasFilters && all.data ? ` of ${totals.total}` : ""})
            </div>
            <div className="flex flex-col gap-space-sm">
              {list.data.map((inv) => (
                <StudyCard key={inv.id} inv={inv} active={inv.external_id === selectedId} onSelect={() => setSelectedId(inv.external_id)} />
              ))}
            </div>
          </div>
          <div className="lg:col-span-7">{selectedId && <StudyDetail key={selectedId} id={selectedId} />}</div>
        </div>
      )}
    </>
  );
}

function Metric({ label, value, tone = "text-on-surface", boxed }: { label: string; value: React.ReactNode; tone?: string; boxed?: boolean }) {
  return (
    <div className={`flex flex-col px-space-md py-space-xs ${boxed ? "rounded-lg bg-surface-container/50" : ""}`}>
      <span className={`t-label tracking-wider ${tone === "text-on-surface" ? "text-on-surface-variant" : tone}`}>{label}</span>
      <span className={`t-headline-md ${tone}`}>{value}</span>
    </div>
  );
}

function StudyCard({ inv, active, onSelect }: { inv: InvestigationSummary; active: boolean; onSelect: () => void }) {
  return (
    <button
      type="button"
      onClick={onSelect}
      aria-pressed={active}
      className={`relative flex flex-col gap-space-xs overflow-hidden rounded-xl p-space-md text-left backdrop-blur-md transition-all ${
        active
          ? "border-l-2 border-amber-glow bg-surface-container/85 shadow-md"
          : "border-l-2 border-transparent bg-surface-container-low/70 hover:bg-surface-container"
      }`}
    >
      <div className="flex items-center justify-between gap-space-sm">
        <span className={`t-headline-md font-bold tracking-tight ${active ? "text-tertiary" : "text-on-surface"}`}>{inv.external_id}</span>
        <span className={`t-code flex items-center gap-1 ${active ? "text-tertiary" : "text-on-surface-variant"}`}>
          <Icon name="local_fire_department" size={16} />
          {inv.run_count} {inv.run_count === 1 ? "run" : "runs"}
        </span>
      </div>
      <p className={`t-body line-clamp-1 ${active ? "font-medium text-on-surface" : "text-on-surface-variant"}`}>{inv.title}</p>
      <div className="flex flex-wrap items-center gap-2 pt-1">
        <GravityChip gravity={inv.gravity_regime} />
        <DomainChip domain={inv.combustion_domain} />
        <span className="t-code ml-auto text-on-surface-variant/60">{inv.publisher}</span>
      </div>
    </button>
  );
}

function StudyDetail({ id }: { id: string }) {
  const { data: inv, error, loading, reload } = useAsync(() => api.investigation(id), [id]);
  if (error) return <ErrorState message={error} onRetry={reload} />;
  if (loading || !inv) return <Loading label="Loading study…" />;
  return <StudyBody inv={inv} />;
}

function StudyBody({ inv }: { inv: InvestigationDetail }) {
  const openProvenance = useProvenance();
  const [visibleCount, setVisibleCount] = useState(30);
  const runs = inv.experiment_runs;
  const visibleRuns = runs.slice(0, visibleCount);
  const focus = typeof inv.source_metadata?.focus === "string" ? inv.source_metadata.focus : null;
  const o2 = runs.map((r) => r.oxygen_fraction).filter((v): v is number => v !== null);
  const o2Range = o2.length ? (Math.min(...o2) === Math.max(...o2) ? pct(o2[0]) : `${pct(Math.min(...o2))} – ${pct(Math.max(...o2))}`) : "—";

  const outcome = OUTCOME_BY_DOMAIN[inv.combustion_domain];
  const points: ChartPoint[] = outcome
    ? runs.flatMap((r) => {
        const m = r.measurements.find((x) => x.canonical_field === outcome.field);
        if (r.flow_velocity_normalized_cm_s === null || !m || m.normalized_value === null) return [];
        return [{ id: r.run_code, label: r.run_code, detail: r.fuel_material, x: r.flow_velocity_normalized_cm_s, y: m.normalized_value, uncertainty: m.uncertainty, earth: r.is_terrestrial_baseline }];
      })
    : [];
  const notPlotted = runs.length - points.length;

  return (
    <div className="flex flex-col gap-space-md">
      {/* Study header */}
      <div className="glass-strong relative flex flex-col gap-space-md overflow-hidden p-space-lg">
        <div className="pointer-events-none absolute -right-16 -top-16 h-56 w-56 rounded-full bg-primary-container/10 blur-3xl" />
        <div className="flex flex-wrap items-center justify-between gap-space-sm">
          <span className="t-code flex items-center gap-1.5 text-secondary">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-secondary" />
            {inv.publisher}
          </span>
          <a href={inv.source_url} target="_blank" rel="noreferrer" className="t-code flex items-center gap-1 text-secondary hover:text-secondary-fixed">
            Original record
            <Icon name="open_in_new" size={16} />
          </a>
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="t-headline-lg font-bold text-tertiary">{inv.external_id}</h2>
          <p className="t-title text-on-surface">{inv.title}</p>
          {focus && <p className="t-body mt-1 leading-relaxed text-on-surface-variant">{focus}</p>}
        </div>
        <div className="grid grid-cols-2 gap-space-sm pt-space-xs sm:grid-cols-4">
          <Stat label="Platform" value={inv.platform} />
          <Stat label="Window" value={yearWindow(inv.start_date, inv.end_date)} />
          <Stat label="Fuel type" value={DOMAIN_LABEL[inv.combustion_domain] ?? inv.combustion_domain} tone="text-primary" />
          <Stat label="O₂ range" value={o2Range} tone="text-secondary" />
        </div>
        <button type="button" onClick={() => openProvenance(inv.external_id)} className="btn-ghost self-start">
          <Icon name="verified_user" size={16} />
          Where this data comes from
        </button>
      </div>

      {/* Runs chart (only when there are enough plottable runs to be useful) */}
      {outcome && points.length >= 2 && (
        <div className="glass flex flex-col gap-space-sm p-space-md">
          <div className="t-label flex items-center gap-1.5 tracking-wider text-on-surface-variant">
            <Icon name="ssid_chart" size={16} className="text-primary" />
            {outcome.label} vs. airflow speed
          </div>
          <ScatterChart points={points} xLabel="Airflow speed (cm/s)" yLabel={outcome.label} yUnit={outcome.unit} height={240} onSelect={openProvenance} />
          {notPlotted > 0 && (
            <p className="t-code px-space-xs text-outline">
              {notPlotted} {notPlotted === 1 ? "run is" : "runs are"} not plotted because a value was not recorded.
            </p>
          )}
        </div>
      )}

      {/* Test runs */}
      <div className="mt-space-xs flex items-center gap-space-sm px-space-xs">
        <span className="t-headline-md text-on-surface">Test runs</span>
        <span className="t-code rounded-full bg-surface-container-high px-space-sm py-0.5 text-on-surface">{runs.length}</span>
      </div>
      {runs.length === 0 ? (
        <EmptyState icon="inbox" title="No test runs recorded for this study" />
      ) : (
        <div className="flex flex-col gap-space-sm">
          {visibleRuns.map((run, i) => (
            <RunCard key={run.id} run={run} defaultOpen={i === 0} />
          ))}
          {runs.length > visibleCount && (
            <button
              type="button"
              onClick={() => setVisibleCount((c) => c + 50)}
              className="btn-ghost self-center"
            >
              Show 50 more runs ({runs.length - visibleCount} remaining)
            </button>
          )}
        </div>
      )}

      <Accordion
        title="Original files"
        badge={<span className="t-code rounded-full bg-surface-container px-space-sm py-0.5 text-on-surface-variant">{inv.source_files.length}</span>}
        hint="File fingerprints"
      >
        <div className="flex flex-col gap-space-sm">
          {inv.source_files.map((f) => (
            <div key={f.id} className="tile flex flex-wrap items-center justify-between gap-space-sm p-space-sm">
              <div className="flex flex-col">
                <span className="t-title break-all text-on-surface">{f.file_name}</span>
                <span className="t-code text-outline">
                  {bytes(f.file_size)} · version {f.version}
                </span>
              </div>
              <span className="t-code text-on-surface-variant" title={f.checksum_sha256}>
                SHA-256 <span className="text-secondary">{shortHash(f.checksum_sha256)}</span>
              </span>
            </div>
          ))}
        </div>
      </Accordion>
    </div>
  );
}

function Stat({ label, value, tone = "text-on-surface" }: { label: string; value: string; tone?: string }) {
  return (
    <div className="tile flex flex-col p-space-sm">
      <span className="t-label tracking-wider text-on-surface-variant/70">{label}</span>
      <span className={`mt-0.5 font-display text-[14px] font-semibold leading-snug ${tone}`}>{value}</span>
    </div>
  );
}

function ConditionChips({ run }: { run: ExperimentRun }) {
  const chip = "t-code rounded-full bg-surface-container-high px-2.5 py-1";
  return (
    <div className="flex flex-wrap items-center gap-2">
      {run.oxygen_fraction !== null ? <span className={`${chip} text-primary`}>O₂ {pct(run.oxygen_fraction)}</span> : <NotRecorded reason={run.oxygen_missing_reason} />}
      {run.pressure_normalized_kpa !== null ? (
        <span className={`${chip} text-on-surface`}>{num(run.pressure_normalized_kpa, 1)} kPa</span>
      ) : (
        <NotRecorded reason={run.pressure_missing_reason} />
      )}
      {run.flow_velocity_normalized_cm_s !== null ? (
        <span className={`${chip} text-secondary`}>{num(run.flow_velocity_normalized_cm_s, 1)} cm/s</span>
      ) : (
        <span className="inline-flex items-center gap-1">
          <span className="t-code text-outline">Airflow</span>
          <NotRecorded reason={run.flow_velocity_missing_reason} />
        </span>
      )}
    </div>
  );
}

function RunCard({ run, defaultOpen }: { run: ExperimentRun; defaultOpen: boolean }) {
  const [open, setOpen] = useState(defaultOpen);
  const openProvenance = useProvenance();
  const notes = typeof run.run_metadata?.notes === "string" && run.run_metadata.notes !== "nan" ? run.run_metadata.notes : null;

  return (
    <div className={`rounded-xl backdrop-blur-xl transition-all ${open ? "bg-surface-container/85 shadow-md" : "bg-surface-container-low/70 hover:bg-surface-container"}`}>
      <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex w-full flex-col gap-space-sm p-space-md text-left sm:flex-row sm:items-center sm:justify-between">
        <span className="flex min-w-0 items-center gap-space-md">
          <span
            className={`shrink-0 rounded-lg px-2.5 py-1 font-display text-[13px] font-bold leading-none ${
              open ? "bg-gradient-to-r from-amber-glow to-amber-deep text-amber-ink shadow-[0_0_14px_rgba(251,191,36,0.35)]" : "bg-surface-container-high text-on-surface"
            }`}
          >
            {run.run_code}
          </span>
          <span className="flex min-w-0 flex-col">
            <span className="font-display text-[15px] font-semibold leading-snug text-on-surface">{run.fuel_material}</span>
            <span className="t-code truncate text-on-surface-variant">{run.test_environment}</span>
          </span>
        </span>
        <span className="flex items-center gap-2">
          <ConditionChips run={run} />
          <Icon name="expand_more" className={`shrink-0 text-on-surface-variant transition-transform ${open ? "rotate-180" : ""}`} />
        </span>
      </button>

      {open && (
        <div className="flex flex-col gap-space-md px-space-md pb-space-md">
          <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-2 xl:grid-cols-3">
            {run.measurements.map((m) => (
              <MeasurementTile key={m.id} m={m} />
            ))}
          </div>

          <dl className="t-code grid grid-cols-1 gap-x-space-lg gap-y-1 text-on-surface-variant sm:grid-cols-2">
            {run.pressure_value !== null && run.pressure_unit !== "kPa" && (
              <Fact label="Pressure as reported">
                {num(run.pressure_value, 2)} {run.pressure_unit} → {num(run.pressure_normalized_kpa, 2)} kPa
              </Fact>
            )}
            {run.flow_velocity_value !== null && run.flow_velocity_unit !== "cm/s" && (
              <Fact label="Airflow as reported">
                {num(run.flow_velocity_value, 3)} {run.flow_velocity_unit} → {num(run.flow_velocity_normalized_cm_s, 2)} cm/s
              </Fact>
            )}
            {run.temperature_value !== null && (
              <Fact label="Ambient temperature">
                {num(run.temperature_value, 1)} °{run.temperature_unit}
              </Fact>
            )}
            {run.droplet_diameter_mm !== null && <Fact label="Droplet diameter">{num(run.droplet_diameter_mm, 2)} mm</Fact>}
            {run.sample_orientation && <Fact label="Setup">{run.sample_orientation.replace(/_/g, " ")}</Fact>}
            <Fact label="Oxidizer">{run.oxidizer}</Fact>
          </dl>

          {run.derived_results.map((d) => (
            <div key={d.id} className="tile flex flex-col gap-0.5 p-space-sm">
              <div className="flex items-baseline justify-between gap-space-sm">
                <span className="t-label tracking-wider text-on-surface-variant">Calculated · {d.result_name}</span>
                <span className="t-title text-tertiary">{num(d.result_value, 4)}</span>
              </div>
              <span className="t-code text-outline">{d.explanation}</span>
            </div>
          ))}

          {notes && <p className="t-body italic text-on-surface-variant">“{notes}”</p>}

          <button type="button" onClick={() => openProvenance(run.run_code)} className="t-code flex items-center gap-1 self-end font-medium text-secondary hover:text-secondary-fixed">
            Where this data comes from
            <Icon name="arrow_forward" size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

function Fact({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-space-md">
      <dt className="text-outline">{label}</dt>
      <dd className="text-right text-on-surface">{children}</dd>
    </div>
  );
}

function MeasurementTile({ m }: { m: Measurement }) {
  const has = m.normalized_value !== null && m.value_status !== "missing" && m.value_status !== "not_applicable";
  return (
    <div className="flex flex-col rounded-lg bg-surface-container-high/50 p-space-md">
      <span className="t-label tracking-wider text-on-surface-variant">{fieldLabel(m.canonical_field)}</span>
      <div className="mt-1 flex min-h-[32px] items-baseline gap-1">
        {has ? (
          <>
            <span className="font-display text-[26px] font-bold leading-none text-tertiary">{num(m.normalized_value, 3)}</span>
            <span className="t-code text-on-surface-variant">
              {m.normalized_unit}
              {m.uncertainty ? ` ± ${num(m.uncertainty, 3)}` : ""}
            </span>
          </>
        ) : (
          <NotRecorded reason={m.missing_reason} />
        )}
      </div>
      {(m.measurement_method || m.notes) && <span className="mt-1 line-clamp-2 font-display text-[11px] text-on-surface-variant/70">{has ? m.measurement_method : m.notes || m.measurement_method}</span>}
    </div>
  );
}
