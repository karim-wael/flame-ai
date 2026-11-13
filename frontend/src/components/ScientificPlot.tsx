"use client";

import React, { useState } from "react";
import { CompareRankedItem } from "@/lib/types";

interface ScientificPlotProps {
  microgravityItems: CompareRankedItem[];
  baselineItems: CompareRankedItem[];
  targetDomain: string;
  targetFlowCmS: number;
  targetO2: number;
  onSelectProvenance: (runCode: string) => void;
}

export default function ScientificPlot({
  microgravityItems,
  baselineItems,
  targetDomain,
  targetFlowCmS,
  targetO2,
  onSelectProvenance,
}: ScientificPlotProps) {
  const [unitMode, setUnitMode] = useState<"normalized" | "original">("normalized");
  const [hoveredRun, setHoveredRun] = useState<CompareRankedItem | null>(null);

  const outcomeFieldByDomain: Record<string, { field: string; label: string; unit: string }> = {
    solid: { field: "flame_spread_rate", label: "Flame Spread Rate", unit: "mm/s" },
    gas: { field: "flame_height", label: "Laminar Flame Length", unit: "mm" },
    liquid_droplet: { field: "burning_rate", label: "Burning Rate Constant (K)", unit: "mm²/s" },
    aerosol_smoke: { field: "smoke_particle_size", label: "Smoke Count Median Diameter", unit: "µm" },
  };

  const activeOutcome = outcomeFieldByDomain[targetDomain] || outcomeFieldByDomain.solid;

  const extractOutcomeVal = (item: CompareRankedItem) => {
    const m = item.outcomes.find((o) => o.canonical_field === activeOutcome.field);
    if (!m) return { val: null, missingReason: "not_reported", unit: activeOutcome.unit, unc: null };
    return {
      val: unitMode === "normalized" ? m.normalized_value : m.value_numeric,
      missingReason: m.missing_reason,
      unit: (unitMode === "normalized" ? m.normalized_unit : m.unit) || activeOutcome.unit,
      unc: m.uncertainty || null,
    };
  };

  const allPlottable = [...microgravityItems, ...baselineItems].map((item) => {
    const out = extractOutcomeVal(item);
    return {
      item,
      x: item.flow_velocity_normalized_cm_s,
      y: out.val,
      unc: out.unc,
      missingX: item.flow_velocity_normalized_cm_s === null,
      missingY: out.val === null,
      missingReason: out.missingReason || item.missing_features[0]?.missing_reason || null,
    };
  });

  const validPoints = allPlottable.filter((p) => p.x !== null && p.y !== null) as {
    item: CompareRankedItem;
    x: number;
    y: number;
    unc: number | null;
    missingX: boolean;
    missingY: boolean;
    missingReason: string | null;
  }[];

  const missingPoints = allPlottable.filter((p) => p.x === null || p.y === null);

  const maxX = Math.max(25, targetFlowCmS * 1.3, ...validPoints.map((p) => p.x * 1.15));
  const maxY = Math.max(2.0, ...validPoints.map((p) => (p.y + (p.unc || 0)) * 1.2));

  const width = 760;
  const height = 340;
  const padL = 64;
  const padR = 32;
  const padT = 28;
  const padB = 52;
  const plotW = width - padL - padR;
  const plotH = height - padT - padB;

  const toSvgX = (x: number) => padL + Math.min(1, Math.max(0, x / maxX)) * plotW;
  const toSvgY = (y: number) => padT + plotH - Math.min(1, Math.max(0, y / maxY)) * plotH;

  // Unique supporting investigations & source files for Acceptance Checklist item #7
  const supportingSources = Array.from(
    new Map(
      [...microgravityItems, ...baselineItems].map((item) => [
        item.investigation_external_id,
        {
          extId: item.investigation_external_id,
          title: item.investigation_title,
          publisher: item.publisher,
          doi: item.doi,
          file: item.source_file_name,
          checksum: item.source_file_checksum,
          url: item.source_url,
          isBaseline: item.is_terrestrial_baseline,
        },
      ])
    ).values()
  );

  return (
    <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-5 shadow-lg">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-orange-500" />
            <h3 className="text-base font-semibold text-white">
              Scientific Condition vs. Outcome Plot ({targetDomain.toUpperCase()} Domain)
            </h3>
          </div>
          <p className="mt-0.5 text-xs text-slate-400">
            Forced Oxidizer Flow Velocity (cm/s) vs. {activeOutcome.label} ({activeOutcome.unit}) — Hover any point for DOI & file provenance
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setUnitMode("normalized")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              unitMode === "normalized"
                ? "bg-orange-500/20 text-orange-300 border border-orange-500/40"
                : "bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200"
            }`}
          >
            Canonical Normalized Units
          </button>
          <button
            onClick={() => setUnitMode("original")}
            className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
              unitMode === "original"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                : "bg-slate-900 text-slate-400 border border-slate-800 hover:text-slate-200"
            }`}
          >
            Original Source Units
          </button>
        </div>
      </div>

      {/* Interactive SVG Scientific Plot */}
      <div className="relative mt-4 overflow-x-auto">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full min-w-[620px] rounded-lg bg-[#080b12] border border-slate-800/70"
        >
          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
            const y = padT + plotH * (1 - t);
            const val = (maxY * t).toFixed(2);
            return (
              <g key={`gy-${i}`}>
                <line x1={padL} y1={y} x2={width - padR} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                <text x={padL - 8} y={y + 4} textAnchor="end" className="fill-slate-400 text-[10px]">
                  {val}
                </text>
              </g>
            );
          })}

          {[0, 0.25, 0.5, 0.75, 1].map((t, i) => {
            const x = padL + plotW * t;
            const val = (maxX * t).toFixed(1);
            return (
              <g key={`gx-${i}`}>
                <line x1={x} y1={padT} x2={x} y2={padT + plotH} stroke="#1e293b" strokeDasharray="3 3" />
                <text x={x} y={padT + plotH + 18} textAnchor="middle" className="fill-slate-400 text-[10px]">
                  {val}
                </text>
              </g>
            );
          })}

          {/* Target Flow Velocity Reference Line */}
          <line
            x1={toSvgX(targetFlowCmS)}
            y1={padT}
            x2={toSvgX(targetFlowCmS)}
            y2={padT + plotH}
            stroke="#f97316"
            strokeWidth={1.5}
            strokeDasharray="5 4"
          />
          <text
            x={toSvgX(targetFlowCmS) + 6}
            y={padT + 14}
            className="fill-orange-400 text-[10px] font-medium"
          >
            Target V_air = {targetFlowCmS} cm/s (O₂={(targetO2 * 100).toFixed(1)}%)
          </text>

          {/* Axes labels */}
          <text
            x={padL + plotW / 2}
            y={height - 10}
            textAnchor="middle"
            className="fill-slate-300 text-[11px] font-medium"
          >
            Forced Oxidizer Flow Velocity V_air (cm/s, Canonical Normalized)
          </text>
          <text
            x={16}
            y={padT + plotH / 2}
            textAnchor="middle"
            transform={`rotate(-90, 16, ${padT + plotH / 2})`}
            className="fill-slate-300 text-[11px] font-medium"
          >
            {activeOutcome.label} ({activeOutcome.unit})
          </text>

          {/* Plotted Experiment Runs with Uncertainty Error Bars */}
          {validPoints.map(({ item, x, y, unc }) => {
            const cx = toSvgX(x);
            const cy = toSvgY(y);
            const isBaseline = item.is_terrestrial_baseline;
            return (
              <g
                key={item.run_id}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredRun(item)}
                onClick={() => onSelectProvenance(item.run_code)}
              >
                {unc !== null && unc > 0 && (
                  <>
                    <line
                      x1={cx}
                      y1={toSvgY(y - unc)}
                      x2={cx}
                      y2={toSvgY(y + unc)}
                      stroke={isBaseline ? "#fbbf24" : "#38bdf8"}
                      strokeWidth={1.5}
                    />
                    <line
                      x1={cx - 4}
                      y1={toSvgY(y + unc)}
                      x2={cx + 4}
                      y2={toSvgY(y + unc)}
                      stroke={isBaseline ? "#fbbf24" : "#38bdf8"}
                      strokeWidth={1.5}
                    />
                    <line
                      x1={cx - 4}
                      y1={toSvgY(y - unc)}
                      x2={cx + 4}
                      y2={toSvgY(y - unc)}
                      stroke={isBaseline ? "#fbbf24" : "#38bdf8"}
                      strokeWidth={1.5}
                    />
                  </>
                )}

                {isBaseline ? (
                  <rect
                    x={cx - 6}
                    y={cy - 6}
                    width={12}
                    height={12}
                    fill="#f59e0b"
                    stroke="#fef3c7"
                    strokeWidth={1.5}
                  />
                ) : (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={6.5}
                    fill="#06b6d4"
                    stroke="#cffafe"
                    strokeWidth={1.5}
                  />
                )}

                <text x={cx + 9} y={cy + 3} className="fill-slate-200 text-[10px] font-medium">
                  {item.run_code}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Legend & Hover Inspector */}
        <div className="mt-3 flex flex-wrap items-center justify-between gap-3 text-xs">
          <div className="flex flex-wrap items-center gap-4">
            <span className="flex items-center gap-1.5 text-cyan-300">
              <span className="inline-block h-3 w-3 rounded-full bg-cyan-500 border border-cyan-100" />
              ISS / Spacecraft Microgravity Evidence (0g)
            </span>
            <span className="flex items-center gap-1.5 text-amber-300">
              <span className="inline-block h-3 w-3 bg-amber-500 border border-amber-100" />
              Terrestrial Reference Baseline (1g FSRI / Ground — Separate Track)
            </span>
          </div>

          {hoveredRun && (
            <div className="rounded-lg border border-cyan-500/40 bg-slate-900/90 px-3 py-1.5 text-xs text-slate-200">
              <span className="font-semibold text-cyan-300">{hoveredRun.run_code}</span> ({hoveredRun.investigation_external_id}) •{" "}
              Fuel: {hoveredRun.fuel_material} • D(S, E_i) = <span className="font-mono text-orange-300">{hoveredRun.distance_d}</span> •{" "}
              {unitMode === "original"
                ? `Orig: P=${hoveredRun.pressure_original || "N/A"}, V=${hoveredRun.flow_velocity_original || "NULL"}`
                : `Norm: P=${hoveredRun.pressure_normalized_kpa ?? "NULL"} kPa, V=${hoveredRun.flow_velocity_normalized_cm_s ?? "NULL"} cm/s`}
            </div>
          )}
        </div>
      </div>

      {/* Explicit Missing-Value Notice (Never silently converted to 0) */}
      {missingPoints.length > 0 && (
        <div className="mt-4 rounded-lg border border-rose-500/30 bg-rose-950/20 p-3 text-xs">
          <div className="font-semibold text-rose-300">
            Explicit Missingness Guardrail ({missingPoints.length} compatible run(s) omitted from X/Y coordinate plot — never plotted at 0):
          </div>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {missingPoints.map((mp) => (
              <button
                key={mp.item.run_id}
                onClick={() => onSelectProvenance(mp.item.run_code)}
                className="rounded border border-rose-500/40 bg-rose-950/40 px-2.5 py-1 text-rose-200 hover:bg-rose-900/50"
              >
                <span className="font-mono font-semibold">{mp.item.run_code}</span>:{" "}
                {mp.missingX ? "flow_velocity = NULL" : `${activeOutcome.field} = NULL`} (reason:{" "}
                <span className="underline">{mp.missingReason || "unavailable_in_source"}</span>)
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Supporting Investigations & Source Files Footer (Checklist #7) */}
      <div className="mt-4 border-t border-slate-800/80 pt-3">
        <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          Supporting Investigations, DOIs & Verified Source Files for This Chart
        </div>
        <div className="mt-2 grid gap-2 sm:grid-cols-2">
          {supportingSources.map((src) => (
            <div
              key={src.extId}
              className="flex items-start justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/60 p-2.5 text-xs"
            >
              <div>
                <div className="flex items-center gap-1.5 font-medium text-slate-200">
                  <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-cyan-300">
                    {src.extId}
                  </span>
                  <span>{src.publisher}</span>
                  {src.isBaseline && (
                    <span className="rounded bg-amber-500/20 px-1.5 py-0.5 text-[10px] text-amber-300">
                      1g Earth Baseline
                    </span>
                  )}
                </div>
                <div className="mt-1 text-[11px] text-slate-400">
                  File: <span className="font-mono text-slate-300">{src.file}</span> • SHA-256:{" "}
                  <span className="font-mono text-slate-400">{src.checksum?.slice(0, 12)}…</span>
                </div>
              </div>
              <a
                href={src.url}
                target="_blank"
                rel="noreferrer"
                className="shrink-0 rounded border border-slate-700 bg-slate-800 px-2 py-1 text-[11px] text-orange-300 hover:border-orange-500/50"
              >
                {src.doi ? `DOI: ${src.doi}` : "Source Record ↗"}
              </a>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

