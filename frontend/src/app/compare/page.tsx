"use client";

import React, { useMemo, useState } from "react";
import { useProvenance } from "@/components/ProvenancePanel";
import ScatterChart, { ChartPoint } from "@/components/ScatterChart";
import { useHealth } from "@/components/Shell";
import { Accordion, EmptyState, ErrorState, Icon, Loading, NotRecorded, PageHeader } from "@/components/ui";
import { api, CompareBody } from "@/lib/api";
import { DOMAIN_LABEL, DOMAIN_OPTIONS, fieldLabel, num, OUTCOME_BY_DOMAIN, pct } from "@/lib/format";
import { useAsync, useDebounced } from "@/lib/hooks";
import { CompareRankedItem, CompareResponse } from "@/lib/types";

// `key` = API weight name; `bk` = key used by the flare_ranking engine in feature_breakdown
// (o2 in %, pressure in psi, airflow in cm/s); `scale` converts engine units to display units.
const FEATURES = [
  { key: "oxygen_fraction", bk: "o2_percent", label: "Oxygen", unit: "pts", scale: 1, digits: 1 },
  { key: "pressure_kpa", bk: "pressure_psi", label: "Pressure", unit: "kPa", scale: 6.89476, digits: 1 },
  { key: "flow_velocity_cm_s", bk: "airflow_cm_s", label: "Airflow", unit: "cm/s", scale: 1, digits: 1 },
] as const;

interface Breakdown {
  status: "measured" | "missing";
  target?: number;
  record_value?: number;
  missing_reason?: string;
}

/** Chart x-axis per fuel type: use the condition that is actually recorded for that domain. */
// Liquid uses initial droplet diameter: FLEX matches share the same O2, and burn time vs. diameter
// is the classic droplet-combustion (d²-law) relationship.
const X_AXIS_BY_DOMAIN: Record<string, "flow" | "oxygen" | "diameter"> = {
  solid: "oxygen",
  gas: "flow",
  liquid_droplet: "diameter",
  aerosol_smoke: "flow",
};

function breakdownOf(item: CompareRankedItem, bk: string): Breakdown | undefined {
  return (item.feature_breakdown as unknown as Record<string, Breakdown | undefined>)[bk];
}

function outcomeOf(item: CompareRankedItem, field: string) {
  return item.outcomes.find((o) => o.canonical_field === field) ?? null;
}

/** Plain-language summary of how close a run's conditions are to the target. */
function whyText(item: CompareRankedItem): string {
  const parts = FEATURES.flatMap((f) => {
    const b = breakdownOf(item, f.bk);
    if (!b) return []; // condition not used for this fuel type
    if (b.status !== "measured" || b.record_value === undefined || b.target === undefined) return [`${f.label.toLowerCase()} not recorded`];
    const delta = Math.abs(b.record_value - b.target) * f.scale;
    return [delta < 0.05 ? `${f.label.toLowerCase()} matches exactly` : `${f.label.toLowerCase()} differs by ${num(delta, f.digits)} ${f.unit}`];
  });
  return parts.length ? parts.join(", ") : "closest recorded test conditions";
}

export default function ComparePage() {
  const { health } = useHealth();
  const [domain, setDomain] = useState("solid");
  const [o2, setO2] = useState(21);
  const [pressure, setPressure] = useState(101.3);
  const [flow, setFlow] = useState(8);
  const [weights, setWeights] = useState({ oxygen_fraction: 45, pressure_kpa: 25, flow_velocity_cm_s: 30 });
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const body: CompareBody = useMemo(
    () => ({
      target_domain: domain,
      target_gravity: "microgravity",
      oxygen_fraction: o2 / 100,
      pressure_kpa: pressure,
      flow_velocity_cm_s: flow,
      include_terrestrial_baseline: true,
      weights,
    }),
    [domain, o2, pressure, flow, weights],
  );
  const debounced = useDebounced(body, 250);
  const { data, error, loading, reload } = useAsync(() => api.compare(debounced), [debounced]);

  const weightSum = weights.oxygen_fraction + weights.pressure_kpa + weights.flow_velocity_cm_s;

  return (
    <>
      <PageHeader
        eyebrow={
          <>
            <span className="rounded-full bg-primary-container/20 px-space-sm py-0.5 text-primary">Similarity search</span>
            <span className="text-outline-variant">/</span>
            <span className="text-secondary">Find similar experiments</span>
          </>
        }
        title="Comparison & Similarity Search"
        description="Set the fire conditions you care about. FLARE ranks past space experiments by how close their test conditions were to yours, and shows Earth tests separately."
      >
        {health && (
          <div className="t-code flex items-center gap-space-sm rounded-lg bg-surface-container-low px-space-md py-space-xs text-on-surface">
            <span className="h-2 w-2 rounded-full bg-tertiary" />
            {health.counts.experiment_runs} RUNS INDEXED
          </div>
        )}
      </PageHeader>

      <div className="grid grid-cols-1 items-start gap-space-xl lg:grid-cols-12">
        {/* Left: your conditions */}
        <div className="glass flex flex-col gap-space-lg p-space-lg lg:sticky lg:top-24 lg:col-span-4">
          <div className="flex items-center gap-space-sm">
            <Icon name="tune" size={22} className="text-primary" />
            <h2 className="t-title font-bold tracking-wide text-on-surface">Your Conditions</h2>
          </div>

          <div className="flex flex-col gap-space-xs">
            <span className="t-label tracking-wider text-outline">Fuel type</span>
            <div className="grid grid-cols-2 gap-space-xs rounded-xl bg-surface-container-lowest/80 p-1.5">
              {DOMAIN_OPTIONS.map((d) => (
                <button
                  key={d.value}
                  type="button"
                  aria-pressed={domain === d.value}
                  onClick={() => {
                    setDomain(d.value);
                    setShowAll(false);
                  }}
                  className={`flex items-center justify-center gap-1.5 rounded-lg px-space-sm py-2 font-display text-[14px] font-semibold transition-all ${
                    domain === d.value ? "bg-primary-container text-on-primary-container" : "text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface"
                  }`}
                >
                  <Icon name={d.icon} size={18} />
                  {d.label}
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-space-sm">
            <Slider icon="bubble_chart" label="Oxygen (O₂)" tone="text-primary" accent="#ffb59d" value={o2} display={`${o2.toFixed(1)} %`} min={15} max={40} step={0.5} minLabel="15%" maxLabel="40%" onChange={setO2} />
            <Slider icon="compress" label="Pressure" tone="text-secondary" accent="#7bd0ff" value={pressure} display={`${pressure.toFixed(1)} kPa`} min={20} max={130} step={0.5} minLabel="20 kPa" maxLabel="130 kPa" onChange={setPressure} />
            <Slider icon="speed" label="Airflow speed" tone="text-tertiary" accent="#ffb95f" value={flow} display={`${flow.toFixed(1)} cm/s`} min={0} max={40} step={0.5} minLabel="0 cm/s" maxLabel="40 cm/s" onChange={setFlow} />
          </div>

          <div className="flex flex-col overflow-hidden rounded-xl bg-surface-container-lowest/50">
            <button type="button" aria-expanded={showAdvanced} onClick={() => setShowAdvanced((s) => !s)} className="flex items-center justify-between p-space-md text-left transition-colors hover:bg-surface-container">
              <span className="flex items-center gap-space-sm">
                <Icon name="settings" size={18} className="text-outline" />
                <span className="font-display text-[14px] font-semibold text-on-surface">Advanced: importance weights</span>
              </span>
              <Icon name="expand_more" size={18} className={`text-outline transition-transform ${showAdvanced ? "rotate-180" : ""}`} />
            </button>
            {showAdvanced && (
              <div className="flex flex-col gap-space-md p-space-md pt-0">
                <p className="t-code text-outline">How much each condition counts when ranking matches.</p>
                {FEATURES.map((f) => (
                  <label key={f.key} className="flex flex-col gap-1">
                    <span className="t-code flex justify-between text-on-surface-variant">
                      {f.label}
                      <span className="text-tertiary">{weightSum > 0 ? Math.round((weights[f.key] / weightSum) * 100) : 0}%</span>
                    </span>
                    <input type="range" className="slider" style={{ accentColor: "#ffb95f" }} min={0} max={100} step={5} value={weights[f.key]} onChange={(e) => setWeights((w) => ({ ...w, [f.key]: Number(e.target.value) }))} />
                  </label>
                ))}
              </div>
            )}
          </div>

          <button type="button" onClick={reload} disabled={loading} className="btn-primary w-full">
            <Icon name={loading ? "progress_activity" : "analytics"} className={loading ? "animate-spin" : ""} />
            {loading ? "Ranking…" : "Analyze & Rank Tests"}
          </button>
          <p className="t-code flex items-start gap-1.5 text-outline">
            <Icon name="info" size={14} className="mt-0.5 shrink-0 text-secondary" />
            The match score shows how close the test conditions are. It is not a fire-risk or ignition probability.
          </p>
        </div>

        {/* Right: results */}
        <div className="flex flex-col gap-space-xl lg:col-span-8">
          {error ? <ErrorState message={error} onRetry={reload} /> : !data ? <Loading label="Ranking experiments…" /> : <Results data={data} domain={domain} flow={flow} o2={o2} showAll={showAll} onShowAll={() => setShowAll(true)} />}
        </div>
      </div>
    </>
  );
}

function Slider(props: { icon: string; label: string; tone: string; accent: string; value: number; display: string; min: number; max: number; step: number; minLabel: string; maxLabel: string; onChange: (v: number) => void }) {
  return (
    <label className="flex flex-col gap-1.5 rounded-xl bg-surface-container-lowest/60 p-space-md backdrop-blur-md">
      <span className="flex items-center justify-between">
        <span className="t-label flex items-center gap-1.5 tracking-wider text-on-surface-variant">
          <Icon name={props.icon} size={16} className={props.tone} />
          {props.label}
        </span>
        <span className={`font-display text-[20px] font-bold ${props.tone}`}>{props.display}</span>
      </span>
      <input type="range" className="slider mt-1" style={{ accentColor: props.accent }} min={props.min} max={props.max} step={props.step} value={props.value} onChange={(e) => props.onChange(Number(e.target.value))} />
      <span className="flex justify-between font-display text-[11px] text-outline">
        <span>{props.minLabel}</span>
        <span>{props.maxLabel}</span>
      </span>
    </label>
  );
}

function Results({ data, domain, flow, o2, showAll, onShowAll }: { data: CompareResponse; domain: string; flow: number; o2: number; showAll: boolean; onShowAll: () => void }) {
  const openProvenance = useProvenance();
  const outcome = OUTCOME_BY_DOMAIN[domain] ?? OUTCOME_BY_DOMAIN.solid;
  const ranked = data.compatible_microgravity_ranking;
  const earth = data.terrestrial_baseline_track;
  const excluded = data.excluded_incompatible_domains;

  const xAxis = X_AXIS_BY_DOMAIN[domain] ?? "flow";
  const xCfg: { label: string; short: string; unit: string; target: number | undefined; minMax: number; value: (i: CompareRankedItem) => number | null } =
    xAxis === "oxygen"
      ? { label: "Oxygen (%)", short: "Oxygen", unit: "%", target: o2, minMax: 30, value: (i) => (i.oxygen_fraction !== null ? i.oxygen_fraction * 100 : null) }
      : xAxis === "diameter"
        ? { label: "Initial droplet diameter (mm)", short: "Droplet size", unit: "mm", target: undefined, minMax: 1, value: (i) => outcomeOf(i, "droplet_initial_diameter")?.normalized_value ?? null }
        : { label: "Airflow speed (cm/s)", short: "Airflow speed", unit: "cm/s", target: flow, minMax: 25, value: (i) => i.flow_velocity_normalized_cm_s };

  const plottable = [...ranked, ...earth];
  const points: ChartPoint[] = plottable.flatMap((item) => {
    const m = outcomeOf(item, outcome.field);
    const x = xCfg.value(item);
    if (x === null || !m || m.normalized_value === null) return [];
    // Only the #1 space match is highlighted; the Earth track has its own rank 1 that would overlap.
    return [{ id: item.run_code, label: item.run_code, detail: item.fuel_material, x, y: m.normalized_value, uncertainty: m.uncertainty, earth: item.is_terrestrial_baseline, highlight: item.rank === 1 && !item.is_terrestrial_baseline }];
  });
  const notPlotted = plottable.length - points.length;

  const excludedGroups = Object.entries(
    excluded.reduce<Record<string, { domain: string; count: number }>>((acc, e) => {
      acc[e.investigation_external_id] ??= { domain: e.record_domain, count: 0 };
      acc[e.investigation_external_id].count += 1;
      return acc;
    }, {}),
  );

  const visible = showAll ? ranked : ranked.slice(0, 5);

  return (
    <>
      <div className="glass relative flex flex-col gap-space-md overflow-hidden rounded-2xl p-space-lg">
        <div>
          <div className="t-label mb-1 flex items-center gap-space-xs tracking-wider text-secondary">
            <Icon name="scatter_plot" size={18} />
            Conditions vs. result
          </div>
          <h2 className="t-headline-md text-on-surface">
            {xCfg.short} vs. {outcome.label.charAt(0).toLowerCase() + outcome.label.slice(1)}
          </h2>
        </div>
        {points.length === 0 ? (
          <EmptyState icon="query_stats" title="Nothing to plot for this fuel type">
            The archived {DOMAIN_LABEL[domain].toLowerCase()} runs do not record both {xCfg.short.toLowerCase()} and {outcome.label.toLowerCase()} as numbers, so there is no chart. FLARE never fills missing values with zero. The ranked matches below are still based on the conditions that were recorded.
          </EmptyState>
        ) : (
          <>
            <ScatterChart points={points} xLabel={xCfg.label} xUnit={xCfg.unit} yLabel={outcome.label} yUnit={outcome.unit} targetX={xCfg.target} minXMax={xCfg.minMax} onSelect={openProvenance} />
            {notPlotted > 0 && (
              <p className="t-code px-space-xs text-outline">
                {notPlotted} {notPlotted === 1 ? "run is" : "runs are"} not plotted because the {xCfg.short.toLowerCase()} or the result was not recorded. Missing values are never shown as zero.
              </p>
            )}
          </>
        )}
      </div>

      <div className="flex flex-col gap-space-md">
        <div className="flex flex-wrap items-center justify-between gap-space-sm">
          <div className="flex items-center gap-space-sm">
            <Icon name="equalizer" className="text-primary" />
            <h3 className="t-headline-md text-on-surface">Closest matches ({DOMAIN_LABEL[domain]})</h3>
          </div>
          <span className="t-code text-on-surface-variant">
            Sorted by <span className="font-bold text-primary">closeness of conditions ↓</span>
          </span>
        </div>

        {ranked.length === 0 ? (
          <EmptyState icon="search_off" title="No space experiments for this fuel type">
            There are no microgravity runs of this fuel type in the database yet.
          </EmptyState>
        ) : (
          <div className="flex flex-col gap-space-md">
            {visible.map((item) => (
              <MatchCard key={item.run_id} item={item} outcomeField={outcome.field} />
            ))}
            {!showAll && ranked.length > visible.length && (
              <button type="button" onClick={onShowAll} className="btn-ghost self-center">
                Show all {ranked.length} matches
                <Icon name="expand_more" size={18} />
              </button>
            )}
          </div>
        )}
      </div>

      <div className="flex flex-col gap-space-sm">
        <Accordion
          title="Earth reference tests"
          iconClass="text-tertiary"
          hint="1g ground baseline"
          badge={<span className="t-code rounded-full bg-tertiary-container/30 px-space-sm py-0.5 text-tertiary">{earth.length} tests · shown separately</span>}
        >
          {earth.length === 0 ? (
            <p className="t-body text-on-surface-variant">No Earth-gravity tests exist for this fuel type.</p>
          ) : (
            <>
              <p className="t-body mb-space-sm text-on-surface-variant">On Earth, hot gas rises and pulls in fresh air, so these tests are not ranked together with space experiments.</p>
              <div className="overflow-x-auto">
                <table className="t-code w-full text-left">
                  <thead>
                    <tr className="bg-surface-container-lowest text-[10px] uppercase text-outline">
                      {["Run", "Material", "O₂", "Pressure", "Airflow", outcome.label].map((h) => (
                        <th key={h} className="p-space-sm font-semibold">
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="text-on-surface-variant">
                    {earth.map((t) => {
                      const m = outcomeOf(t, outcome.field);
                      return (
                        <tr key={t.run_id} className="cursor-pointer transition-colors hover:bg-surface-container-high" onClick={() => openProvenance(t.run_code)}>
                          <td className="p-space-sm font-bold text-tertiary">{t.run_code}</td>
                          <td className="p-space-sm">{t.fuel_material}</td>
                          <td className="p-space-sm">{pct(t.oxygen_fraction)}</td>
                          <td className="p-space-sm">{num(t.pressure_normalized_kpa, 1)} kPa</td>
                          <td className="p-space-sm">{num(t.flow_velocity_normalized_cm_s, 1)} cm/s</td>
                          <td className="p-space-sm font-bold text-on-surface">{m && m.normalized_value !== null ? `${num(m.normalized_value, 3)} ${m.normalized_unit}` : <NotRecorded reason={m?.missing_reason} />}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </Accordion>

        <Accordion
          title="Not compared: different fuel types"
          iconClass="text-outline"
          badge={<span className="t-code rounded-full bg-surface-container px-space-sm py-0.5 text-on-surface-variant">{excluded.length} tests left out</span>}
        >
          <p className="t-body mb-space-sm text-on-surface-variant">
            Solids, gases, liquid droplets and smoke burn in physically different ways, so runs of another fuel type are left out of a {DOMAIN_LABEL[domain].toLowerCase()} comparison.
          </p>
          <div className="t-code flex flex-wrap gap-space-xs">
            {excludedGroups.map(([code, g]) => (
              <span key={code} className="rounded bg-surface-container px-space-sm py-1 text-outline">
                {code} · {DOMAIN_LABEL[g.domain] ?? g.domain} ({g.count})
              </span>
            ))}
          </div>
        </Accordion>
      </div>
    </>
  );
}

function MatchCard({ item, outcomeField }: { item: CompareRankedItem; outcomeField: string }) {
  const [open, setOpen] = useState(false);
  const openProvenance = useProvenance();
  const top = item.rank === 1;
  const score = Math.round(item.condition_closeness_index);

  return (
    <div className={`relative overflow-hidden rounded-2xl backdrop-blur-xl transition-all ${top ? "bg-surface-container-low/75 shadow-lg" : "bg-surface-container-low/50 shadow-md"}`}>
      <div className="flex flex-col gap-space-md p-space-lg md:flex-row md:items-center md:justify-between">
        <div className="flex min-w-0 items-center gap-space-md">
          <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl font-display text-[20px] font-bold ${top ? "bg-primary-container text-on-primary-container shadow-md" : "bg-surface-container-high text-on-surface-variant"}`}>
            #{item.rank}
          </div>
          <div className="flex min-w-0 flex-col">
            <div className="flex flex-wrap items-center gap-space-sm">
              <h4 className="font-display text-[20px] font-bold tracking-tight text-on-surface">{item.run_code}</h4>
              <span className="chip bg-secondary/10 text-secondary">{item.investigation_external_id}</span>
            </div>
            <span className="t-body truncate text-on-surface-variant">{item.fuel_material}</span>
            <div className="mt-1 flex flex-wrap items-center gap-x-space-lg gap-y-1 font-display text-[13px] text-on-surface-variant">
              <Cond label="O₂" value={item.oxygen_fraction !== null ? pct(item.oxygen_fraction) : null} tone="text-primary" />
              <Cond label="Press" value={item.pressure_normalized_kpa !== null ? `${num(item.pressure_normalized_kpa, 1)} kPa` : null} tone="text-secondary" />
              <Cond label="Flow" value={item.flow_velocity_normalized_cm_s !== null ? `${num(item.flow_velocity_normalized_cm_s, 1)} cm/s` : null} tone="text-tertiary" />
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between gap-space-lg md:justify-end">
          <div className="flex w-36 flex-col items-end">
            <div className="flex items-baseline gap-1.5">
              <span className="font-display text-[11px] font-semibold uppercase text-outline">Match</span>
              <span className={`font-display text-[22px] font-bold leading-none ${top ? "text-primary" : "text-secondary"}`}>{score}%</span>
            </div>
            <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-surface-container-lowest">
              <div className={`h-full rounded-full ${top ? "bg-primary-container" : "bg-secondary-container"}`} style={{ width: `${score}%` }} />
            </div>
          </div>
          <button type="button" aria-expanded={open} onClick={() => setOpen((o) => !o)} className="flex shrink-0 items-center gap-1.5 rounded-xl bg-surface-container-lowest px-space-md py-2.5 font-display text-[13px] font-semibold text-secondary transition-colors hover:bg-surface-container-high">
            Details
            <Icon name="expand_more" size={18} className={`transition-transform ${open ? "rotate-180" : ""}`} />
          </button>
        </div>
      </div>

      {top && !open && (
        <div className="flex items-center gap-2 bg-surface-container-lowest/80 px-space-lg py-2.5 font-display text-[12px] text-tertiary">
          <Icon name="verified" size={16} className="shrink-0 text-primary" />
          <span>
            <strong className="text-primary">Why #1:</strong> {whyText(item)}.
          </span>
        </div>
      )}

      {open && (
        <div className="flex flex-col gap-space-md bg-surface-container-lowest/70 p-space-lg">
          <div className="grid grid-cols-1 gap-space-sm sm:grid-cols-3">
            {FEATURES.map((f) => {
              const b = breakdownOf(item, f.bk);
              const measured = b?.status === "measured" && b.record_value !== undefined && b.target !== undefined;
              return (
                <div key={f.key} className="tile flex flex-col gap-1 p-space-sm">
                  <span className="t-label tracking-wider text-on-surface-variant">{f.label}</span>
                  {!b ? (
                    <span className="t-code text-outline">Not used for this fuel type</span>
                  ) : measured ? (
                    <>
                      <span className="t-title text-on-surface">
                        {num(b.record_value! * f.scale, f.digits)}
                        <span className="t-code text-outline"> vs your {num(b.target! * f.scale, f.digits)}</span>
                      </span>
                      <span className="t-code text-secondary">
                        {num(Math.abs(b.record_value! - b.target!) * f.scale, f.digits)} {f.unit} apart
                      </span>
                    </>
                  ) : (
                    <NotRecorded reason={b.missing_reason} className="self-start" />
                  )}
                </div>
              );
            })}
          </div>

          <div>
            <span className="t-label tracking-wider text-on-surface-variant">What was measured</span>
            <div className="mt-space-xs flex flex-wrap gap-space-xs">
              {item.outcomes.map((o) => (
                <span key={o.id} className={`t-code inline-flex items-center gap-1.5 rounded-lg px-space-sm py-1 ${o.canonical_field === outcomeField ? "bg-tertiary-container/25 text-tertiary" : "bg-surface-container text-on-surface-variant"}`}>
                  {fieldLabel(o.canonical_field)}:{" "}
                  {o.normalized_value !== null ? (
                    <strong className="text-on-surface">
                      {num(o.normalized_value, 3)} {o.normalized_unit}
                    </strong>
                  ) : (
                    <NotRecorded reason={o.missing_reason} />
                  )}
                </span>
              ))}
            </div>
          </div>

          <button type="button" onClick={() => openProvenance(item.run_code)} className="t-code flex items-center gap-1 self-end font-medium text-secondary hover:text-secondary-fixed">
            Where this data comes from
            <Icon name="arrow_forward" size={16} />
          </button>
        </div>
      )}
    </div>
  );
}

function Cond({ label, value, tone }: { label: string; value: string | null; tone: string }) {
  return (
    <span className="flex items-center gap-1">
      <span className="text-outline">{label}:</span>
      {value ? <strong className={`font-bold ${tone}`}>{value}</strong> : <NotRecorded />}
    </span>
  );
}
