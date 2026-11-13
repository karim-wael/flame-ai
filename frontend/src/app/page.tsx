"use client";

import React, { useEffect, useState } from "react";
import ScientificPlot from "@/components/ScientificPlot";
import {
  AssistantResponse,
  CombustionDomain,
  CompareResponse,
  DataSourceItem,
  GravityRegime,
  InvestigationDetail,
  InvestigationSummary,
} from "@/lib/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const PRESET_QUESTIONS = [
  "Why does flame spread behave differently in microgravity?",
  "How do liquid droplets burn and extinguish in FLEX (PSI-69) vs JAXA Kibo Group Combustion?",
  "How do smoke aerosol particle sizes in SAME and SAME-R affect spacecraft fire detection?",
  "How do co-flow velocity and burner diameter affect soot smoke points in SPICE (PSI-107)?",
  "Why must Earth-based FSRI 1g cone calorimeter data be kept separate from ISS microgravity rankings?",
];

export default function FlareAIDashboard() {
  const [activeTab, setActiveTab] = useState<"explorer" | "compare" | "assistant" | "ingestion">("explorer");

  // Explorer state
  const [sources, setSources] = useState<DataSourceItem[]>([]);
  const [investigations, setInvestigations] = useState<InvestigationSummary[]>([]);
  const [selectedInv, setSelectedInv] = useState<InvestigationDetail | null>(null);
  const [filterSource, setFilterSource] = useState<string>("");
  const [filterDomain, setFilterDomain] = useState<string>("");
  const [filterGravity, setFilterGravity] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Compare state
  const [targetDomain, setTargetDomain] = useState<CombustionDomain>("solid");
  const [targetGravity, setTargetGravity] = useState<GravityRegime>("microgravity");
  const [targetO2, setTargetO2] = useState<number>(0.21);
  const [targetPressureKpa, setTargetPressureKpa] = useState<number>(101.3);
  const [targetFlowCmS, setTargetFlowCmS] = useState<number>(8.0);
  const [includeBaseline, setIncludeBaseline] = useState<boolean>(true);
  const [compareResult, setCompareResult] = useState<CompareResponse | null>(null);
  const [loadingCompare, setLoadingCompare] = useState<boolean>(false);

  // Hybrid RAG Assistant state
  const [question, setQuestion] = useState<string>(PRESET_QUESTIONS[0]);
  const [ragDomainFilter, setRagDomainFilter] = useState<string>("");
  const [ragGravityFilter, setRagGravityFilter] = useState<string>("");
  const [assistantResult, setAssistantResult] = useState<AssistantResponse | null>(null);
  const [loadingAssistant, setLoadingAssistant] = useState<boolean>(false);

  // Provenance Drawer / Modal
  const [provenanceData, setProvenanceData] = useState<Record<string, unknown> | null>(null);
  const [ingestionReport, setIngestionReport] = useState<Record<string, unknown> | null>(null);
  const [runningIngestion, setRunningIngestion] = useState<boolean>(false);

  // Fetch sources & investigations
  useEffect(() => {
    fetch(`${API_BASE}/api/sources`)
      .then((r) => r.json())
      .then((d) => setSources(d))
      .catch(console.error);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (filterSource) params.set("source", filterSource);
    if (filterDomain) params.set("domain", filterDomain);
    if (filterGravity) params.set("gravity", filterGravity);
    if (searchQuery) params.set("search", searchQuery);

    fetch(`${API_BASE}/api/investigations?${params.toString()}`)
      .then((r) => r.json())
      .then((list: InvestigationSummary[]) => {
        setInvestigations(list);
        if (list.length > 0 && (!selectedInv || !list.some((i) => i.external_id === selectedInv.external_id))) {
          loadInvestigationDetail(list[0].external_id);
        }
      })
      .catch(console.error);
  }, [filterSource, filterDomain, filterGravity, searchQuery]);

  const loadInvestigationDetail = async (extId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/investigations/${extId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedInv(data);
      }
    } catch (err) {
      console.error(err);
    }
  };

  // Run comparison whenever parameters change or tab opens
  const executeComparison = async () => {
    setLoadingCompare(true);
    try {
      const res = await fetch(`${API_BASE}/api/compare`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          target_domain: targetDomain,
          target_gravity: targetGravity,
          oxygen_fraction: targetO2,
          pressure_kpa: targetPressureKpa,
          flow_velocity_cm_s: targetFlowCmS,
          include_terrestrial_baseline: includeBaseline,
          weights: {
            oxygen_fraction: 0.45,
            pressure_kpa: 0.25,
            flow_velocity_cm_s: 0.3,
          },
        }),
      });
      if (res.ok) {
        setCompareResult(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingCompare(false);
    }
  };

  useEffect(() => {
    executeComparison();
  }, [targetDomain, targetGravity, targetO2, targetPressureKpa, targetFlowCmS, includeBaseline]);

  // Run Hybrid RAG query
  const executeAssistantQuery = async (qText?: string) => {
    const activeQ = qText ?? question;
    if (!activeQ.trim()) return;
    setLoadingAssistant(true);
    try {
      const res = await fetch(`${API_BASE}/api/assistant/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: activeQ,
          combustion_domain: ragDomainFilter || null,
          gravity_regime: ragGravityFilter || null,
          top_k_chunks: 4,
          top_k_experiments: 5,
        }),
      });
      if (res.ok) {
        setAssistantResult(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingAssistant(false);
    }
  };

  useEffect(() => {
    executeAssistantQuery(PRESET_QUESTIONS[0]);
  }, []);

  const openProvenance = async (recordId: string) => {
    try {
      const res = await fetch(`${API_BASE}/api/provenance/${recordId}`);
      if (res.ok) {
        setProvenanceData(await res.json());
      }
    } catch (err) {
      console.error(err);
    }
  };

  const triggerReingestion = async () => {
    setRunningIngestion(true);
    try {
      const res = await fetch(`${API_BASE}/api/ingestion/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_filter: "ALL", force_refresh: true }),
      });
      if (res.ok) {
        setIngestionReport(await res.json());
      }
    } catch (err) {
      console.error(err);
    } finally {
      setRunningIngestion(false);
    }
  };

  const domainBadgeColor = (dom: string) => {
    switch (dom) {
      case "solid":
        return "bg-orange-500/20 text-orange-300 border-orange-500/40";
      case "gas":
        return "bg-cyan-500/20 text-cyan-300 border-cyan-500/40";
      case "liquid_droplet":
        return "bg-emerald-500/20 text-emerald-300 border-emerald-500/40";
      case "aerosol_smoke":
        return "bg-purple-500/20 text-purple-300 border-purple-500/40";
      default:
        return "bg-slate-800 text-slate-300 border-slate-700";
    }
  };

  const gravityBadgeColor = (grav: string, isBaseline?: boolean) => {
    if (isBaseline || grav === "normal_gravity") {
      return "bg-amber-500/20 text-amber-300 border-amber-500/40";
    }
    return "bg-sky-500/20 text-sky-300 border-sky-500/40";
  };

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top Scientific Prototype Guardrail Banner (Acceptance Checklist #9) */}
      <div className="border-b border-orange-500/30 bg-gradient-to-r from-orange-950/60 via-slate-900 to-cyan-950/60 px-6 py-2 text-xs text-orange-200 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="rounded bg-orange-500 px-1.5 py-0.5 text-[10px] font-bold uppercase text-black">
            Decision-Support Prototype
          </span>
          <span>
            <strong>FLARE AI</strong> is a scientific research & decision-support prototype for{" "}
            <strong>NASA Space Apps Challenge 2026 (Flame in Freefall)</strong> — NOT a certified spacecraft fire-safety system.
          </span>
        </div>
        <span className="font-mono text-[11px] text-slate-300">
          Sources: NASA PSI (P0/P1) • JAXA DARTS Kibo GCE (P1) • UL FSRI MaP 1g Baseline (P2)
        </span>
      </div>

      {/* Main Header & Navigation */}
      <header className="border-b border-slate-800/80 bg-[#0a0e17]/90 backdrop-blur sticky top-0 z-20 px-6 py-4">
        <div className="mx-auto max-w-7xl flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-orange-500 to-amber-600 font-bold text-black shadow-lg shadow-orange-500/20">
              FL
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-white">
                FLARE AI — Microgravity Combustion & Hybrid Knowledge Platform
              </h1>
              <p className="text-xs text-slate-400">
                Canonical Normalization • Domain-Gated Similarity • Hybrid RAG (Vector + Keyword + PostgreSQL)
              </p>
            </div>
          </div>

          <nav className="flex flex-wrap items-center gap-2">
            {[
              { id: "explorer", label: "1. Experiment Explorer" },
              { id: "compare", label: "2. Domain-Gated Comparison" },
              { id: "assistant", label: "3. Hybrid RAG Assistant" },
              { id: "ingestion", label: "4. Ingestion & Provenance Pipeline" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as typeof activeTab)}
                className={`rounded-lg px-3.5 py-2 text-xs font-semibold transition ${
                  activeTab === tab.id
                    ? "bg-orange-500 text-black shadow-md shadow-orange-500/20"
                    : "bg-slate-900 text-slate-300 border border-slate-800 hover:border-slate-700"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="mx-auto w-full max-w-7xl flex-1 px-6 py-6">
        {/* =====================================================================
            TAB 1: EXPERIMENT EXPLORER
           ===================================================================== */}
        {activeTab === "explorer" && (
          <div className="space-y-6">
            {/* Filters Bar */}
            <div className="grid gap-3 rounded-xl border border-slate-800 bg-[#0d121d] p-4 sm:grid-cols-4">
              <div>
                <label className="block text-[11px] font-semibold uppercase text-slate-400">Publisher / Source</label>
                <select
                  value={filterSource}
                  onChange={(e) => setFilterSource(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100"
                >
                  <option value="">All Registered Publishers (3)</option>
                  <option value="NASA PSI">NASA PSI (Primary — P0/P1)</option>
                  <option value="JAXA DARTS">JAXA DARTS Kibo GCE (External 0g — P1)</option>
                  <option value="UL FSRI">UL FSRI MaP (Earth 1g Baseline — P2)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-slate-400">Combustion Domain</label>
                <select
                  value={filterDomain}
                  onChange={(e) => setFilterDomain(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100"
                >
                  <option value="">All Combustion Domains</option>
                  <option value="solid">solid (BASS-II, SAFFIRE-I, FSRI)</option>
                  <option value="gas">gas (SPICE Co-flow Jets)</option>
                  <option value="liquid_droplet">liquid_droplet (FLEX, JAXA Kibo GC)</option>
                  <option value="aerosol_smoke">aerosol_smoke (SAME, SAME-R)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-slate-400">Gravity Regime</label>
                <select
                  value={filterGravity}
                  onChange={(e) => setFilterGravity(e.target.value)}
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100"
                >
                  <option value="">All Gravity Regimes</option>
                  <option value="microgravity">microgravity (ISS / Cygnus / Kibo 0g)</option>
                  <option value="normal_gravity">normal_gravity (Earth 1g Baseline)</option>
                </select>
              </div>

              <div>
                <label className="block text-[11px] font-semibold uppercase text-slate-400">Search Investigations</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="PSI-25, BASS-II, SPICE, n-decane..."
                  className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500"
                />
              </div>
            </div>

            {/* Split View: Investigations List (Left) + Detailed Runs & Measurements (Right) */}
            <div className="grid gap-6 lg:grid-cols-12">
              <div className="lg:col-span-4 space-y-3">
                <div className="flex items-center justify-between text-xs text-slate-400 px-1">
                  <span>Verified Investigations ({investigations.length})</span>
                  <span>Priority P0–P2</span>
                </div>
                {investigations.map((inv) => {
                  const isSelected = selectedInv?.external_id === inv.external_id;
                  return (
                    <button
                      key={inv.id}
                      onClick={() => loadInvestigationDetail(inv.external_id)}
                      className={`w-full text-left rounded-xl border p-4 transition ${
                        isSelected
                          ? "border-orange-500 bg-orange-950/20 shadow-md"
                          : "border-slate-800 bg-[#0d121d] hover:border-slate-700"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs font-bold text-orange-300">
                          {inv.external_id}
                        </span>
                        <span className="rounded bg-slate-800/90 px-2 py-0.5 text-[11px] font-medium text-slate-300">
                          {inv.publisher} • {inv.priority}
                        </span>
                      </div>
                      <h3 className="mt-2 text-sm font-semibold text-white">{inv.title}</h3>
                      <div className="mt-2.5 flex flex-wrap gap-1.5">
                        <span className={`rounded border px-2 py-0.5 text-[10px] font-medium ${domainBadgeColor(inv.combustion_domain)}`}>
                          domain: {inv.combustion_domain}
                        </span>
                        <span className={`rounded border px-2 py-0.5 text-[10px] font-medium ${gravityBadgeColor(inv.gravity_regime)}`}>
                          gravity: {inv.gravity_regime}
                        </span>
                      </div>
                      <div className="mt-2.5 flex items-center justify-between text-[11px] text-slate-400">
                        <span>{inv.doi ? `DOI: ${inv.doi}` : "External Archive Link"}</span>
                        <span>{inv.run_count} runs</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Right Column: Selected Investigation Detail */}
              <div className="lg:col-span-8">
                {selectedInv ? (
                  <div className="space-y-5 rounded-xl border border-slate-800 bg-[#0d121d] p-5">
                    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-slate-800 pb-4">
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="rounded bg-orange-500/20 border border-orange-500/40 px-2.5 py-0.5 font-mono text-xs font-bold text-orange-300">
                            {selectedInv.external_id}
                          </span>
                          <span className={`rounded border px-2.5 py-0.5 text-xs font-medium ${domainBadgeColor(selectedInv.combustion_domain)}`}>
                            {selectedInv.combustion_domain}
                          </span>
                          <span className={`rounded border px-2.5 py-0.5 text-xs font-medium ${gravityBadgeColor(selectedInv.gravity_regime)}`}>
                            {selectedInv.gravity_regime}
                          </span>
                          {selectedInv.domain_track === "terrestrial_baseline" && (
                            <span className="rounded border border-amber-500/50 bg-amber-500/20 px-2.5 py-0.5 text-xs font-semibold text-amber-300">
                              Earth-Based 1g Reference Track
                            </span>
                          )}
                        </div>
                        <h2 className="mt-2 text-lg font-bold text-white">{selectedInv.title}</h2>
                        <p className="mt-1 text-xs text-slate-400">
                          Platform: <strong className="text-slate-200">{selectedInv.platform}</strong> • Version:{" "}
                          <span className="font-mono text-slate-300">{selectedInv.version}</span> • Dates:{" "}
                          {selectedInv.start_date} → {selectedInv.end_date}
                        </p>
                      </div>

                      <div className="flex flex-col items-end gap-2">
                        <a
                          href={selectedInv.source_url}
                          target="_blank"
                          rel="noreferrer"
                          className="rounded-lg border border-orange-500/40 bg-orange-500/10 px-3 py-1.5 text-xs font-semibold text-orange-300 hover:bg-orange-500/20"
                        >
                          Official Source Repository ↗
                        </a>
                        {selectedInv.doi && (
                          <span className="font-mono text-[11px] text-cyan-300">DOI: {selectedInv.doi}</span>
                        )}
                      </div>
                    </div>

                    {/* Source File Inventory with SHA-256 Checksums (Checklist #2) */}
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Verified Source Files & SHA-256 Checksums
                      </h4>
                      <div className="mt-2 grid gap-2">
                        {selectedInv.source_files.map((sf) => (
                          <div
                            key={sf.id}
                            className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-800 bg-slate-900/70 px-3.5 py-2 text-xs"
                          >
                            <div>
                              <span className="font-mono font-semibold text-cyan-300">{sf.file_name}</span>{" "}
                              <span className="text-slate-400">
                                ({sf.file_role}, {sf.file_size} bytes, version {sf.version})
                              </span>
                            </div>
                            <div className="font-mono text-[11px] text-slate-400">
                              SHA-256: <span className="text-emerald-400">{sf.checksum_sha256.slice(0, 20)}…</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Experiment Runs & Canonical Measurements Table */}
                    <div>
                      <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
                        Experiment Runs, Original vs. Canonical Units & Explicit Missingness ({selectedInv.experiment_runs.length})
                      </h4>
                      <div className="mt-2.5 space-y-3">
                        {selectedInv.experiment_runs.map((run) => (
                          <div
                            key={run.id}
                            className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-slate-700 transition"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex flex-wrap items-center gap-2">
                                <span className="rounded bg-slate-800 px-2.5 py-1 font-mono text-xs font-bold text-white">
                                  {run.run_code}
                                </span>
                                <span className="text-sm font-semibold text-orange-300">{run.fuel_material}</span>
                                <span className="text-xs text-slate-400">({run.burner_or_sample_geometry})</span>
                              </div>
                              <button
                                onClick={() => openProvenance(run.run_code)}
                                className="rounded-lg border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-1 text-xs font-medium text-cyan-300 hover:bg-cyan-500/20"
                              >
                                Inspect Full Provenance & Audit Trail
                              </button>
                            </div>

                            {/* Environmental Conditions Row */}
                            <div className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4 text-xs">
                              <div className="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                                <span className="text-[10px] uppercase text-slate-400">Oxygen Fraction</span>
                                <div className="mt-0.5 font-mono text-slate-200">
                                  {run.oxygen_fraction !== null ? (
                                    `${run.oxygen_fraction} (${(run.oxygen_fraction * 100).toFixed(1)}%)`
                                  ) : (
                                    <span className="text-rose-400">NULL ({run.oxygen_missing_reason})</span>
                                  )}
                                </div>
                              </div>

                              <div className="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                                <span className="text-[10px] uppercase text-slate-400">Pressure (Orig → Canonical)</span>
                                <div className="mt-0.5 font-mono text-slate-200">
                                  {run.pressure_normalized_kpa !== null ? (
                                    `${run.pressure_value} ${run.pressure_unit} → ${run.pressure_normalized_kpa} kPa`
                                  ) : (
                                    <span className="text-rose-400">NULL ({run.pressure_missing_reason})</span>
                                  )}
                                </div>
                              </div>

                              <div className="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                                <span className="text-[10px] uppercase text-slate-400">Flow Velocity (Orig → Canonical)</span>
                                <div className="mt-0.5 font-mono text-slate-200">
                                  {run.flow_velocity_normalized_cm_s !== null ? (
                                    `${run.flow_velocity_value} ${run.flow_velocity_unit} → ${run.flow_velocity_normalized_cm_s} cm/s`
                                  ) : (
                                    <span className="text-rose-400">NULL ({run.flow_velocity_missing_reason})</span>
                                  )}
                                </div>
                              </div>

                              <div className="rounded-lg bg-slate-950/70 p-2 border border-slate-800/80">
                                <span className="text-[10px] uppercase text-slate-400">Gravity & Orientation</span>
                                <div className="mt-0.5 font-mono text-slate-200">
                                  {run.gravity_regime} • {run.sample_orientation}
                                </div>
                              </div>
                            </div>

                            {/* Measurements Table */}
                            <div className="mt-3 overflow-x-auto">
                              <table className="w-full text-left text-xs">
                                <thead>
                                  <tr className="border-b border-slate-800 text-[11px] text-slate-400">
                                    <th className="py-1.5 pr-3">Canonical Field</th>
                                    <th className="py-1.5 pr-3">Source Variable</th>
                                    <th className="py-1.5 pr-3">Original Value</th>
                                    <th className="py-1.5 pr-3">Canonical Normalized</th>
                                    <th className="py-1.5 pr-3">Status / Missing Reason</th>
                                    <th className="py-1.5">Method</th>
                                  </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-800/60">
                                  {run.measurements.map((m) => (
                                    <tr key={m.id}>
                                      <td className="py-1.5 pr-3 font-mono font-semibold text-cyan-300">
                                        {m.canonical_field}
                                      </td>
                                      <td className="py-1.5 pr-3 font-mono text-slate-300">{m.variable_name}</td>
                                      <td className="py-1.5 pr-3 font-mono text-slate-200">
                                        {m.value_numeric !== null ? `${m.value_numeric} ${m.unit || ""}` : "NULL"}
                                      </td>
                                      <td className="py-1.5 pr-3 font-mono text-emerald-300">
                                        {m.normalized_value !== null
                                          ? `${m.normalized_value} ${m.normalized_unit || ""}${
                                              m.uncertainty ? ` (±${m.uncertainty})` : ""
                                            }`
                                          : "NULL"}
                                      </td>
                                      <td className="py-1.5 pr-3">
                                        {m.value_status === "measured" ? (
                                          <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] text-emerald-300">
                                            measured
                                          </span>
                                        ) : (
                                          <span className="rounded bg-rose-500/20 border border-rose-500/40 px-2 py-0.5 text-[10px] font-semibold text-rose-300">
                                            {m.value_status}: {m.missing_reason}
                                          </span>
                                        )}
                                      </td>
                                      <td className="py-1.5 text-slate-400">{m.measurement_method || m.notes}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-8 text-center text-sm text-slate-400">
                    Select an investigation on the left to inspect its raw files, SHA-256 checksums, and canonical measurements.
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* =====================================================================
            TAB 2: DOMAIN-GATED SCIENTIFIC COMPARISON & SIMILARITY ENGINE
           ===================================================================== */}
        {activeTab === "compare" && (
          <div className="space-y-6">
            {/* Target Environmental Conditions Controls */}
            <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-800 pb-3">
                <div>
                  <h2 className="text-base font-bold text-white">
                    Domain-Gated Explainable Similarity Ranking Engine
                  </h2>
                  <p className="text-xs text-slate-400">
                    Formula: <code className="text-orange-300">D(S, E_i) = √[ w₁(ΔO₂)² + w₂(ΔP)² + w₃(ΔV_air)² ]</code> —
                    Blocks incompatible combustion domains by default & isolates 1g FSRI terrestrial baselines
                  </p>
                </div>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeBaseline}
                    onChange={(e) => setIncludeBaseline(e.target.checked)}
                    className="rounded border-slate-700 bg-slate-900"
                  />
                  Show Separated Earth-Based 1g Reference Track (FSRI MaP)
                </label>
              </div>

              <div className="mt-4 grid gap-4 sm:grid-cols-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    1. Target Combustion Domain Gate
                  </label>
                  <select
                    value={targetDomain}
                    onChange={(e) => setTargetDomain(e.target.value as CombustionDomain)}
                    className="mt-1.5 w-full rounded-lg border border-orange-500/50 bg-slate-900 px-3 py-2 text-xs font-semibold text-orange-300"
                  >
                    <option value="solid">solid (BASS-II, SAFFIRE-I)</option>
                    <option value="gas">gas (SPICE Laminar Jets)</option>
                    <option value="liquid_droplet">liquid_droplet (FLEX & JAXA Kibo GC)</option>
                    <option value="aerosol_smoke">aerosol_smoke (SAME & SAME-R)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    2. Target Oxygen Fraction:{" "}
                    <span className="font-mono text-cyan-300">{(targetO2 * 100).toFixed(1)}% O₂</span>
                  </label>
                  <input
                    type="range"
                    min={0.16}
                    max={0.3}
                    step={0.005}
                    value={targetO2}
                    onChange={(e) => setTargetO2(parseFloat(e.target.value))}
                    className="mt-2 w-full accent-orange-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>16% (Hypoxic)</span>
                    <span>21% (ISS Cabin)</span>
                    <span>30% (Exploration)</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    3. Target Cabin Pressure:{" "}
                    <span className="font-mono text-cyan-300">{targetPressureKpa.toFixed(1)} kPa</span>
                  </label>
                  <input
                    type="range"
                    min={65}
                    max={125}
                    step={1}
                    value={targetPressureKpa}
                    onChange={(e) => setTargetPressureKpa(parseFloat(e.target.value))}
                    className="mt-2 w-full accent-orange-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>70 kPa (10.2 psia)</span>
                    <span>101.3 kPa (1 atm)</span>
                    <span>122 kPa</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-300">
                    4. Target Forced Flow V_air:{" "}
                    <span className="font-mono text-cyan-300">{targetFlowCmS.toFixed(1)} cm/s</span>
                  </label>
                  <input
                    type="range"
                    min={0.5}
                    max={25.0}
                    step={0.5}
                    value={targetFlowCmS}
                    onChange={(e) => setTargetFlowCmS(parseFloat(e.target.value))}
                    className="mt-2 w-full accent-orange-500"
                  />
                  <div className="flex justify-between text-[10px] text-slate-500">
                    <span>1 cm/s (Quiescent)</span>
                    <span>8 cm/s (MSG Fan)</span>
                    <span>20 cm/s (SAFFIRE)</span>
                  </div>
                </div>
              </div>
            </div>

            {compareResult && (
              <>
                {/* Interactive Scientific Plot with Provenance Footer */}
                <ScientificPlot
                  microgravityItems={compareResult.compatible_microgravity_ranking}
                  baselineItems={compareResult.terrestrial_baseline_track}
                  targetDomain={targetDomain}
                  targetFlowCmS={targetFlowCmS}
                  targetO2={targetO2}
                  onSelectProvenance={openProvenance}
                />

                {/* Compatible Microgravity Ranking Table */}
                <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <h3 className="text-sm font-bold text-white">
                      Compatible Microgravity Ranking ({compareResult.compatible_microgravity_ranking.length} runs in{" "}
                      <span className="text-orange-400">{targetDomain}</span> domain)
                    </h3>
                    <span className="text-[11px] text-slate-400">
                      Sorted by Weighted Normalized Distance D(S, E_i) — Lower distance = closer experimental conditions
                    </span>
                  </div>

                  <div className="mt-3 space-y-2.5">
                    {compareResult.compatible_microgravity_ranking.map((item) => (
                      <div
                        key={item.run_id}
                        className="rounded-lg border border-slate-800 bg-slate-900/50 p-3.5 flex flex-wrap items-center justify-between gap-4"
                      >
                        <div className="space-y-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded bg-orange-500 px-2 py-0.5 font-mono text-xs font-bold text-black">
                              #{item.rank}
                            </span>
                            <span className="font-mono text-sm font-bold text-white">{item.run_code}</span>
                            <span className="rounded bg-slate-800 px-2 py-0.5 font-mono text-xs text-cyan-300">
                              {item.investigation_external_id} ({item.publisher})
                            </span>
                            <span className="text-xs font-semibold text-orange-300">{item.fuel_material}</span>
                            {item.missing_features.map((mf, i) => (
                              <span
                                key={i}
                                className="rounded border border-rose-500/40 bg-rose-950/40 px-2 py-0.5 text-[10px] font-semibold text-rose-300"
                              >
                                Missing {mf.feature}: {mf.missing_reason} (Not zero-filled)
                              </span>
                            ))}
                          </div>
                          <p className="text-xs text-slate-300">{item.explanation}</p>
                          <div className="text-[11px] text-slate-400 font-mono">
                            O₂={item.oxygen_fraction ?? "NULL"} • P={item.pressure_normalized_kpa ?? "NULL"} kPa (
                            {item.pressure_original}) • V_air={item.flow_velocity_normalized_cm_s ?? "NULL"} cm/s (
                            {item.flow_velocity_original || "NULL"})
                          </div>
                        </div>

                        <div className="flex items-center gap-4">
                          <div className="text-right">
                            <div className="text-[10px] uppercase text-slate-400">Distance D(S, E_i)</div>
                            <div className="font-mono text-base font-bold text-cyan-300">{item.distance_d}</div>
                            <div className="text-[11px] text-emerald-400">
                              Closeness Index: {item.condition_closeness_index}/100
                            </div>
                          </div>
                          <button
                            onClick={() => openProvenance(item.run_code)}
                            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-slate-200 hover:border-cyan-500/50"
                          >
                            Provenance
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Separated Terrestrial 1g Baseline Track (Acceptance Checklist #8) */}
                {includeBaseline && compareResult.terrestrial_baseline_track.length > 0 && (
                  <div className="rounded-xl border border-amber-500/40 bg-amber-950/10 p-5">
                    <div className="flex items-center justify-between gap-2">
                      <div>
                        <span className="rounded bg-amber-500/20 border border-amber-500/40 px-2 py-0.5 text-[10px] font-bold uppercase text-amber-300">
                          Separated Earth-Based Reference Track (1g)
                        </span>
                        <h3 className="mt-1 text-sm font-bold text-amber-200">
                          FSRI MaP & Ground 1g Baseline Records ({compareResult.terrestrial_baseline_track.length}) — Never Ranked Inside 0g Microgravity Evidence
                        </h3>
                      </div>
                    </div>
                    <div className="mt-3 grid gap-2.5 sm:grid-cols-2">
                      {compareResult.terrestrial_baseline_track.map((tb) => (
                        <div key={tb.run_id} className="rounded-lg border border-amber-500/30 bg-slate-900/80 p-3 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="font-mono font-bold text-amber-300">
                              {tb.run_code} ({tb.investigation_external_id})
                            </span>
                            <span className="text-[11px] text-slate-400">{tb.publisher}</span>
                          </div>
                          <div className="mt-1 font-semibold text-white">{tb.fuel_material}</div>
                          <div className="mt-1 text-[11px] text-amber-200/80">{tb.baseline_separation_note}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Blocked Incompatible Domains Panel (Acceptance Checklist #6) */}
                <div className="rounded-xl border border-rose-500/30 bg-rose-950/10 p-5">
                  <h3 className="text-sm font-bold text-rose-300">
                    Domain Gate Audit: Excluded Incompatible Combustion Domains (
                    {compareResult.excluded_incompatible_domains.length} runs blocked)
                  </h3>
                  <p className="mt-0.5 text-xs text-slate-400">
                    Per Section 7 Scientific Comparison Rules, solid, gas, liquid-droplet, and smoke/aerosol experiments have
                    fundamentally different governing physics and are blocked from cross-domain ranking by default.
                  </p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                    {compareResult.excluded_incompatible_domains.slice(0, 6).map((ex) => (
                      <div key={ex.run_id} className="rounded-lg border border-rose-500/20 bg-slate-900/70 p-2.5 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="font-mono font-bold text-rose-300">{ex.run_code}</span>
                          <span className="rounded bg-rose-500/20 px-1.5 py-0.5 text-[10px] text-rose-200">
                            {ex.record_domain} ≠ {ex.target_domain}
                          </span>
                        </div>
                        <div className="mt-1 text-[11px] text-slate-300">{ex.fuel_material}</div>
                        <div className="mt-1 text-[11px] text-slate-400">{ex.rejection_reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* =====================================================================
            TAB 3: HYBRID KNOWLEDGE ARCHITECTURE & RAG RESEARCH ASSISTANT
           ===================================================================== */}
        {activeTab === "assistant" && (
          <div className="space-y-6">
            {/* Query Box & Preset Scientific Questions */}
            <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h2 className="text-base font-bold text-white">
                    FLARE AI Hybrid Knowledge Research Assistant (Semantic Vector + Keyword + PostgreSQL SQL)
                  </h2>
                  <p className="text-xs text-slate-400">
                    Retrieves published reports from the Knowledge Base + structured experiments from PostgreSQL, and strictly
                    separates <strong>Published Scientific Findings</strong> from <strong>Generated Interpretation</strong>.
                  </p>
                </div>
              </div>

              {/* Preset Question Pills */}
              <div className="mt-3 flex flex-wrap gap-2">
                {PRESET_QUESTIONS.map((pq, i) => (
                  <button
                    key={i}
                    onClick={() => {
                      setQuestion(pq);
                      executeAssistantQuery(pq);
                    }}
                    className={`rounded-lg border px-3 py-1.5 text-xs transition ${
                      question === pq
                        ? "border-orange-500 bg-orange-500/20 text-orange-200"
                        : "border-slate-800 bg-slate-900 text-slate-300 hover:border-slate-700"
                    }`}
                  >
                    {pq}
                  </button>
                ))}
              </div>

              <div className="mt-4 flex flex-wrap gap-3">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && executeAssistantQuery()}
                  placeholder="Ask a scientific question about microgravity combustion..."
                  className="flex-1 min-w-[260px] rounded-lg border border-slate-700 bg-slate-900 px-4 py-2.5 text-sm text-white"
                />
                <select
                  value={ragDomainFilter}
                  onChange={(e) => setRagDomainFilter(e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs text-slate-200"
                >
                  <option value="">All Domains</option>
                  <option value="solid">solid</option>
                  <option value="gas">gas</option>
                  <option value="liquid_droplet">liquid_droplet</option>
                  <option value="aerosol_smoke">aerosol_smoke</option>
                </select>
                <button
                  onClick={() => executeAssistantQuery()}
                  disabled={loadingAssistant}
                  className="rounded-lg bg-orange-500 px-5 py-2.5 text-xs font-bold text-black hover:bg-orange-400 disabled:opacity-50"
                >
                  {loadingAssistant ? "Running Hybrid Retrieval..." : "Run Hybrid RAG + SQL Query"}
                </button>
              </div>
            </div>

            {assistantResult && (
              <>
                {/* Hybrid Retrieval Pipeline Execution Trace */}
                <div className="grid gap-3 sm:grid-cols-4">
                  {assistantResult.retrieval_pipeline_trace.map((step, i) => (
                    <div key={i} className="rounded-xl border border-slate-800 bg-[#0d121d] p-3.5">
                      <div className="text-xs font-bold text-cyan-300">{step.step}</div>
                      <p className="mt-1 text-[11px] text-slate-400">{step.detail}</p>
                    </div>
                  ))}
                </div>

                {/* Split View: Left = Published Evidence & SQL Records | Right = Clearly Labeled Generated Synthesis */}
                <div className="grid gap-6 lg:grid-cols-12">
                  {/* Left 7 Cols: Verbatim Published Scientific Evidence + SQL Experiment Records */}
                  <div className="lg:col-span-7 space-y-5">
                    <div className="rounded-xl border border-emerald-500/40 bg-[#0d121d] p-5">
                      <div className="flex items-center justify-between">
                        <span className="rounded bg-emerald-500/20 border border-emerald-500/40 px-2.5 py-0.5 text-[11px] font-bold uppercase text-emerald-300">
                          1. Verbatim Published Evidence (Knowledge Base Chunks)
                        </span>
                        <span className="text-xs text-slate-400">
                          Semantic + Keyword Hybrid Retrieval
                        </span>
                      </div>

                      <div className="mt-3 space-y-3">
                        {assistantResult.published_scientific_evidence.map((chunk) => (
                          <div
                            key={chunk.chunk_id}
                            className="rounded-lg border border-slate-800 bg-slate-900/70 p-3.5 text-xs"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="rounded bg-slate-800 px-2 py-0.5 font-mono font-bold text-orange-300">
                                  {chunk.external_investigation_id}
                                </span>
                                <span className="font-semibold text-white">{chunk.section_title}</span>
                              </div>
                              <span className="font-mono text-[11px] text-emerald-400">
                                Hybrid Score: {chunk.hybrid_score} (Sem: {chunk.semantic_score}, KW: {chunk.keyword_score})
                              </span>
                            </div>
                            <p className="mt-2 leading-relaxed text-slate-200">{chunk.content_text}</p>
                            <div className="mt-2.5 flex flex-wrap items-center justify-between gap-2 border-t border-slate-800 pt-2 text-[11px] text-slate-400">
                              <span>
                                Source: <strong className="text-slate-300">{chunk.document_title}</strong> ({chunk.authors},{" "}
                                {chunk.publication_year})
                              </span>
                              <a
                                href={chunk.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="text-cyan-300 hover:underline"
                              >
                                {chunk.doi ? `DOI: ${chunk.doi} ↗` : "Source Archive ↗"}
                              </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Matched Structured Experiments from PostgreSQL */}
                    <div className="rounded-xl border border-cyan-500/40 bg-[#0d121d] p-5">
                      <div className="flex items-center justify-between">
                        <span className="rounded bg-cyan-500/20 border border-cyan-500/40 px-2.5 py-0.5 text-[11px] font-bold uppercase text-cyan-300">
                          2. Retrieved Structured Experiments (PostgreSQL SQL Query)
                        </span>
                        <span className="text-xs text-slate-400">
                          Domain, Fuel & Gravity Aware
                        </span>
                      </div>

                      <div className="mt-3 space-y-2.5">
                        {assistantResult.structured_sql_experiments.map((exp) => (
                          <div
                            key={exp.run_id}
                            className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs"
                          >
                            <div className="flex flex-wrap items-center justify-between gap-2">
                              <div className="flex items-center gap-2">
                                <span className="font-mono font-bold text-white">{exp.run_code}</span>
                                <span className="rounded bg-slate-800 px-1.5 py-0.5 font-mono text-[11px] text-orange-300">
                                  {exp.external_investigation_id}
                                </span>
                                <span className={`rounded border px-1.5 py-0.5 text-[10px] ${domainBadgeColor(exp.combustion_domain)}`}>
                                  {exp.combustion_domain}
                                </span>
                                <span className={`rounded border px-1.5 py-0.5 text-[10px] ${gravityBadgeColor(exp.gravity_regime, exp.is_terrestrial_baseline)}`}>
                                  {exp.gravity_regime}
                                </span>
                              </div>
                              <button
                                onClick={() => openProvenance(exp.run_code)}
                                className="text-[11px] text-cyan-300 hover:underline"
                              >
                                Provenance ↗
                              </button>
                            </div>
                            <div className="mt-1.5 text-slate-300">
                              Fuel: <strong>{exp.fuel_material}</strong> • O₂={exp.oxygen_fraction ?? "NULL"} • P=
                              {exp.pressure_normalized_kpa ?? "NULL"} kPa • V_air=
                              {exp.flow_velocity_normalized_cm_s ?? `NULL (${exp.flow_velocity_missing_reason})`} cm/s
                            </div>
                            <div className="mt-1.5 flex flex-wrap gap-2">
                              {exp.measurements.map((m) => (
                                <span
                                  key={m.id}
                                  className={`rounded px-2 py-0.5 font-mono text-[11px] ${
                                    m.value_status === "measured"
                                      ? "bg-slate-800 text-emerald-300"
                                      : "bg-rose-950/60 text-rose-300 border border-rose-500/30"
                                  }`}
                                >
                                  {m.canonical_field}:{" "}
                                  {m.value_status === "measured"
                                    ? `${m.normalized_value} ${m.normalized_unit}`
                                    : `NULL (${m.missing_reason})`}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  {/* Right 5 Cols: Clearly Labeled Generated Interpretation with Citations */}
                  <div className="lg:col-span-5 space-y-4">
                    <div className="rounded-xl border border-orange-500/50 bg-gradient-to-b from-orange-950/20 to-[#0d121d] p-5">
                      <div className="flex items-center justify-between gap-2 border-b border-orange-500/30 pb-3">
                        <span className="rounded bg-orange-500 px-2.5 py-0.5 text-[11px] font-bold uppercase text-black">
                          3. Generated Scientific Interpretation
                        </span>
                        <span className="font-mono text-[11px] text-orange-300">
                          {assistantResult.generated_interpretation.synthesis_mode}
                        </span>
                      </div>

                      <div className="mt-2 rounded-lg border border-orange-500/20 bg-orange-950/20 px-3 py-2 text-[11px] text-orange-200">
                        {assistantResult.generated_interpretation.label}
                      </div>

                      <div className="mt-4 whitespace-pre-line text-xs leading-relaxed text-slate-200">
                        {assistantResult.generated_interpretation.markdown_content}
                      </div>

                      <div className="mt-5 border-t border-slate-800 pt-3">
                        <div className="text-[11px] font-semibold uppercase text-slate-400">
                          Grounded Citations & DOIs Used
                        </div>
                        <div className="mt-2 space-y-1.5">
                          {assistantResult.generated_interpretation.citations.map((cit, idx) => (
                            <div
                              key={idx}
                              className="flex items-center justify-between rounded bg-slate-900/80 px-2.5 py-1.5 text-xs"
                            >
                              <span className="text-slate-200">
                                <strong className="text-orange-300">[{cit.external_id}]</strong> {cit.publisher}
                              </span>
                              <a
                                href={cit.source_url}
                                target="_blank"
                                rel="noreferrer"
                                className="font-mono text-[11px] text-cyan-300 hover:underline"
                              >
                                {cit.doi ? `DOI: ${cit.doi}` : "Repository Link ↗"}
                              </a>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* =====================================================================
            TAB 4: 7-STEP INGESTION WORKFLOW & PROVENANCE REGISTRY
           ===================================================================== */}
        {activeTab === "ingestion" && (
          <div className="space-y-6">
            <div className="rounded-xl border border-slate-800 bg-[#0d121d] p-5 flex flex-wrap items-center justify-between gap-4">
              <div>
                <h2 className="text-base font-bold text-white">
                  7-Stage Scientific Ingestion Pipeline & Canonical Field Mappings
                </h2>
                <p className="text-xs text-slate-400">
                  1. Discover → 2. Acquire (Raw SHA-256) → 3. Parse → 4. Normalize → 5. Validate → 6. Publish → 7. Audit
                </p>
              </div>
              <button
                onClick={triggerReingestion}
                disabled={runningIngestion}
                className="rounded-lg bg-emerald-500 px-4 py-2 text-xs font-bold text-black hover:bg-emerald-400 disabled:opacity-50"
              >
                {runningIngestion ? "Executing 7-Stage Pipeline..." : "Trigger Verified Re-Ingestion Job"}
              </button>
            </div>

            {ingestionReport && (
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/15 p-4 text-xs">
                <div className="font-bold text-emerald-300">Ingestion Job Completed Successfully</div>
                <pre className="mt-2 overflow-x-auto font-mono text-[11px] text-slate-200">
                  {JSON.stringify(ingestionReport, null, 2)}
                </pre>
              </div>
            )}

            <div className="grid gap-4">
              {sources.map((src) => (
                <div key={src.id} className="rounded-xl border border-slate-800 bg-[#0d121d] p-5">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <span className="rounded bg-orange-500/20 px-2 py-0.5 font-mono text-xs font-bold text-orange-300">
                        {src.publisher} ({src.priority})
                      </span>
                      <h3 className="mt-1 text-sm font-bold text-white">{src.source_name}</h3>
                      <p className="text-xs text-slate-400">
                        License: {src.license} • Access Date: {src.access_date} • Track:{" "}
                        <span className="font-mono text-cyan-300">{src.domain_track}</span>
                      </p>
                    </div>
                    <a
                      href={src.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs text-orange-300"
                    >
                      Source URL ↗
                    </a>
                  </div>

                  <div className="mt-4">
                    <div className="text-[11px] font-semibold uppercase text-slate-400">
                      Canonical Unit Transformations & Field Mappings ({src.field_mappings.length})
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-2">
                      {src.field_mappings.map((fm) => (
                        <div key={fm.id} className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-xs">
                          <div className="font-mono font-semibold text-cyan-300">
                            {fm.source_field} ({fm.source_unit}) → {fm.canonical_field} ({fm.canonical_unit})
                          </div>
                          <div className="mt-1 text-slate-300">{fm.transform_description}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Provenance Modal Drawer */}
      {provenanceData && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4">
          <div className="max-h-[85vh] w-full max-w-2xl overflow-y-auto rounded-2xl border border-cyan-500/40 bg-[#0d121d] p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-cyan-300">
                Record Provenance, Checksum & Transformation Audit Trail
              </h3>
              <button
                onClick={() => setProvenanceData(null)}
                className="rounded-lg bg-slate-800 px-3 py-1 text-xs font-semibold text-slate-200 hover:bg-slate-700"
              >
                Close ✕
              </button>
            </div>
            <pre className="mt-4 overflow-x-auto rounded-lg bg-slate-950 p-4 font-mono text-xs text-slate-200">
              {JSON.stringify(provenanceData, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}

