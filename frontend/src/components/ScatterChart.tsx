"use client";

import React, { useState } from "react";
import { num } from "@/lib/format";

export interface ChartPoint {
  id: string;
  label: string;
  detail?: string;
  x: number;
  y: number;
  uncertainty?: number | null;
  earth: boolean;
  highlight?: boolean;
}

interface Props {
  points: ChartPoint[];
  xLabel: string;
  xUnit?: string;
  yLabel: string;
  yUnit: string;
  targetX?: number;
  minXMax?: number;
  height?: number;
  onSelect?: (id: string) => void;
}

const W = 760;
const PAD = { l: 64, r: 28, t: 30, b: 46 };

function niceMax(v: number): number {
  if (v <= 0) return 1;
  const pow = Math.pow(10, Math.floor(Math.log10(v)));
  const n = v / pow;
  const step = [1, 2, 2.5, 3, 4, 5, 6, 8, 10].find((s) => n <= s) ?? 10;
  return step * pow;
}

export default function ScatterChart({ points, xLabel, xUnit = "cm/s", yLabel, yUnit, targetX, minXMax = 10, height = 300, onSelect }: Props) {
  const [hover, setHover] = useState<ChartPoint | null>(null);
  const plotW = W - PAD.l - PAD.r;
  const plotH = height - PAD.t - PAD.b;

  const maxX = niceMax(Math.max(minXMax, targetX ?? 0, ...points.map((p) => p.x)) * 1.05);
  const maxY = niceMax(Math.max(...points.map((p) => p.y + (p.uncertainty ?? 0)), 0.0001) * 1.1);
  const sx = (x: number) => PAD.l + (Math.min(Math.max(x, 0), maxX) / maxX) * plotW;
  const sy = (y: number) => PAD.t + plotH - (Math.min(Math.max(y, 0), maxY) / maxY) * plotH;
  const ticks = [0, 0.25, 0.5, 0.75, 1];

  return (
    <div className="flex flex-col gap-space-sm">
      <div className="rounded-lg bg-surface-container-lowest/60 p-space-xs">
        <svg viewBox={`0 0 ${W} ${height}`} className="h-auto w-full" role="img" aria-label={`${yLabel} against ${xLabel}`}>
          {ticks.map((t) => {
            const y = PAD.t + plotH * (1 - t);
            const x = PAD.l + plotW * t;
            return (
              <g key={t}>
                <line x1={PAD.l} x2={W - PAD.r} y1={y} y2={y} stroke="#313540" strokeDasharray="4 4" />
                <text x={PAD.l - 8} y={y + 4} textAnchor="end" fill="#a98a80" fontSize="11" fontFamily="var(--font-grotesk)">
                  {num(maxY * t, 2)}
                </text>
                <text x={x} y={PAD.t + plotH + 18} textAnchor="middle" fill="#a98a80" fontSize="11" fontFamily="var(--font-grotesk)">
                  {num(maxX * t, 1)}
                </text>
              </g>
            );
          })}
          <line x1={PAD.l} x2={W - PAD.r} y1={PAD.t + plotH} y2={PAD.t + plotH} stroke="#594139" strokeWidth="1.5" />
          <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={PAD.t + plotH} stroke="#594139" strokeWidth="1.5" />
          <text x={PAD.l + plotW / 2} y={height - 6} textAnchor="middle" fill="#dfe2f1" fontSize="11" fontFamily="var(--font-grotesk)">
            {xLabel}
          </text>
          <text x={16} y={PAD.t + plotH / 2} textAnchor="middle" transform={`rotate(-90 16 ${PAD.t + plotH / 2})`} fill="#dfe2f1" fontSize="11" fontFamily="var(--font-grotesk)">
            {yLabel} ({yUnit})
          </text>

          {targetX !== undefined && (
            <g>
              <line x1={sx(targetX)} x2={sx(targetX)} y1={PAD.t - 4} y2={PAD.t + plotH} stroke="#ff6b35" strokeWidth="2" strokeDasharray="6 4" />
              <rect x={Math.min(Math.max(sx(targetX) - 52, PAD.l), W - PAD.r - 104)} y={6} width={104} height={20} rx={4} fill="#1c1f2a" stroke="#ff6b35" />
              <text x={Math.min(Math.max(sx(targetX), PAD.l + 52), W - PAD.r - 52)} y={20} textAnchor="middle" fill="#ffb59d" fontSize="10" fontWeight="700" fontFamily="var(--font-grotesk)">
                TARGET: {num(targetX, 1)} {xUnit}
              </text>
            </g>
          )}

          {points.map((p) => {
            const cx = sx(p.x);
            const cy = sy(p.y);
            const color = p.earth ? "#ffb95f" : "#7bd0ff";
            return (
              <g
                key={p.id}
                tabIndex={onSelect ? 0 : undefined}
                className={onSelect ? "cursor-pointer outline-none" : undefined}
                onMouseEnter={() => setHover(p)}
                onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(p)}
                onBlur={() => setHover(null)}
                onClick={() => onSelect?.(p.id)}
                onKeyDown={(e) => e.key === "Enter" && onSelect?.(p.id)}
              >
                {p.uncertainty ? (
                  <line x1={cx} x2={cx} y1={sy(p.y - p.uncertainty)} y2={sy(p.y + p.uncertainty)} stroke={color} strokeOpacity="0.6" strokeWidth="1.5" />
                ) : null}
                {p.highlight && <circle cx={cx} cy={cy} r={11} fill="#ff6b35" fillOpacity="0.3" />}
                {p.earth ? (
                  <rect x={cx - 5} y={cy - 5} width={10} height={10} rx={1.5} fill={color} opacity={0.9} />
                ) : (
                  <circle cx={cx} cy={cy} r={p.highlight ? 6 : 5} fill={p.highlight ? "#ffb59d" : color} opacity={0.92} />
                )}
                {/* Larger invisible hit target */}
                <circle cx={cx} cy={cy} r={14} fill="transparent" />
                {(p.highlight || hover?.id === p.id) && (
                  <text x={cx > W - 150 ? cx - 10 : cx + 10} y={cy - 8} textAnchor={cx > W - 150 ? "end" : "start"} fill={p.highlight ? "#ffb59d" : "#dfe2f1"} fontSize="11" fontWeight="700" fontFamily="var(--font-grotesk)">
                    {p.label}
                  </text>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="t-code flex min-h-[20px] flex-wrap items-center justify-between gap-space-sm px-space-xs text-on-surface-variant">
        <div className="flex flex-wrap items-center gap-space-md">
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-full bg-secondary" /> Space (microgravity)
          </span>
          <span className="flex items-center gap-1.5">
            <span className="inline-block h-2.5 w-2.5 rounded-sm bg-tertiary" /> Earth (1g) reference
          </span>
        </div>
        {hover ? (
          <span className="text-on-surface">
            <strong className="text-secondary">{hover.label}</strong>
            {hover.detail ? ` · ${hover.detail}` : ""} · {num(hover.x, 1)} {xUnit} · {num(hover.y, 3)} {yUnit}
          </span>
        ) : (
          <span className="text-outline">{points.length ? "Hover a point for details" : "No plottable values"}</span>
        )}
      </div>
    </div>
  );
}
