"use client";

import React, { useRef, useState } from "react";
import Markdown from "@/components/Markdown";
import { useProvenance } from "@/components/ProvenancePanel";
import { useHealth } from "@/components/Shell";
import { Accordion, CopyButton, DomainChip, EmptyState, ErrorState, GravityChip, Icon, NotRecorded, PageHeader, Select } from "@/components/ui";
import { api } from "@/lib/api";
import { doiUrl, fieldLabel, num, pct } from "@/lib/format";
import { AssistantResponse } from "@/lib/types";

const SUGGESTIONS = [
  { icon: "bolt", text: "Why does flame spread behave differently in microgravity?" },
  { icon: "water_drop", text: "How do liquid droplets burn and extinguish in FLEX (PSI-69)?" },
  { icon: "blur_on", text: "How do smoke particle sizes in SAME and SAME-R affect spacecraft fire detection?" },
  { icon: "air", text: "How does co-flow velocity affect soot smoke points in SPICE?" },
  { icon: "public", text: "Why must Earth-based cone calorimeter data be kept separate from microgravity results?" },
];

const SOURCE_TONES = [
  { chip: "bg-secondary/15 text-secondary border-secondary/20", rule: "border-secondary/40", link: "text-secondary", border: "rgba(123, 208, 255, 0.16)" },
  { chip: "bg-primary/15 text-primary border-primary/20", rule: "border-primary/40", link: "text-primary", border: "rgba(255, 181, 157, 0.18)" },
  { chip: "bg-tertiary/15 text-tertiary border-tertiary/20", rule: "border-tertiary/40", link: "text-tertiary", border: "rgba(255, 185, 95, 0.18)" },
];

export default function AssistantPage() {
  const { health } = useHealth();
  const [question, setQuestion] = useState("");
  const [domain, setDomain] = useState("");
  const [gravity, setGravity] = useState("");
  const [fuel, setFuel] = useState("");
  const [result, setResult] = useState<AssistantResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const callId = useRef(0);

  const ask = async (text?: string) => {
    const q = (text ?? question).trim();
    if (q.length < 3 || loading) return;
    const id = ++callId.current;
    setLoading(true);
    setError(null);
    try {
      const res = await api.ask({
        question: q,
        combustion_domain: domain || null,
        gravity_regime: gravity || null,
        fuel_filter: fuel.trim() || null,
        top_k_chunks: 4,
        top_k_experiments: 5,
      });
      if (id === callId.current) setResult(res);
    } catch (e) {
      if (id === callId.current) setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      if (id === callId.current) setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-space-xl">
      <PageHeader
        eyebrow={
          <>
            <span className="text-primary">Copilot</span>
            <span className="text-outline-variant">|</span>
            <span className="text-secondary">Answers with sources</span>
          </>
        }
        title="Research Assistant"
        description="Ask a combustion science question in plain language. The answer is built from the source passages and experiments in the FLARE database, and every source is listed below it."
      >
        {health && (
          <div className="flex flex-wrap items-center gap-space-md">
            <Pill dot="bg-secondary">{health.counts.knowledge_chunks} SOURCE PASSAGES</Pill>
            <Pill dot="bg-primary-container">{health.counts.experiment_runs} TEST RUNS</Pill>
          </div>
        )}
      </PageHeader>

      {/* Query console */}
      <div
        className="relative flex flex-col gap-space-md overflow-hidden rounded-xl p-space-lg shadow-xl"
        style={{ background: "linear-gradient(145deg, rgba(16, 24, 52, 0.75), rgba(9, 14, 30, 0.85))", border: "1px solid rgba(123, 208, 255, 0.18)" }}
      >
        <div className="pointer-events-none absolute -right-16 -top-16 h-80 w-80 rounded-full bg-gradient-to-br from-primary-container/15 via-secondary/10 to-transparent blur-3xl" />
        <form
          className="relative z-10 flex flex-col items-stretch gap-space-sm md:flex-row"
          onSubmit={(e) => {
            e.preventDefault();
            ask();
          }}
        >
          <div className="relative flex flex-1 items-center rounded-lg px-space-md shadow-inner" style={{ background: "rgba(10, 16, 36, 0.85)", border: "1px solid rgba(123, 208, 255, 0.2)" }}>
            <Icon name="neurology" className="mr-space-sm text-secondary" />
            <input
              type="text"
              aria-label="Your question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask about flame spread, extinction, smoke, droplets…"
              className="w-full bg-transparent py-space-md font-display text-[16px] font-medium text-on-surface placeholder:text-outline focus:outline-none"
            />
            {question && (
              <button type="button" aria-label="Clear question" onClick={() => setQuestion("")} className="p-space-xs text-on-surface-variant hover:text-on-surface">
                <Icon name="cancel" size={18} />
              </button>
            )}
          </div>
          <button type="submit" disabled={loading || question.trim().length < 3} className="btn-amber px-space-xl">
            <Icon name={loading ? "progress_activity" : "local_fire_department"} className={loading ? "animate-spin" : ""} />
            {loading ? "Searching…" : "Ask Copilot"}
          </button>
        </form>

        <div className="z-10 flex flex-col gap-space-xs">
          <div className="t-label flex items-center gap-space-xs tracking-wider text-outline">
            <Icon name="lightbulb" size={14} />
            Try one of these
          </div>
          <div className="flex flex-wrap gap-space-xs">
            {SUGGESTIONS.map((s) => {
              const active = question === s.text;
              return (
                <button
                  key={s.text}
                  type="button"
                  onClick={() => {
                    setQuestion(s.text);
                    ask(s.text);
                  }}
                  className={`t-code flex items-center gap-space-xs rounded-full px-space-md py-space-xs text-left shadow-sm transition-colors ${
                    active ? "font-semibold text-amber-light" : "bg-surface-container-high text-on-surface-variant hover:bg-surface-bright hover:text-on-surface"
                  }`}
                  style={active ? { background: "rgba(245, 158, 11, 0.18)", border: "1px solid rgba(251, 191, 36, 0.6)" } : { border: "1px solid transparent" }}
                >
                  <Icon name={s.icon} size={14} />
                  {s.text}
                </button>
              );
            })}
          </div>
        </div>

        <div className="z-10 flex flex-col gap-space-xs">
          <div className="t-label flex items-center gap-space-xs tracking-wider text-outline">
            <Icon name="tune" size={14} />
            Narrow the search (optional)
          </div>
          <div className="flex flex-wrap items-center gap-space-sm">
            <Select label="Fuel type" value={domain} onChange={setDomain}>
              <option value="">Any fuel type</option>
              <option value="solid">Solid fuel</option>
              <option value="gas">Gas flame</option>
              <option value="liquid_droplet">Liquid droplet</option>
              <option value="aerosol_smoke">Smoke</option>
            </Select>
            <Select label="Gravity" value={gravity} onChange={setGravity}>
              <option value="">Space and Earth</option>
              <option value="microgravity">Space (microgravity)</option>
              <option value="normal_gravity">Earth (1g)</option>
            </Select>
            <input type="text" aria-label="Material" value={fuel} onChange={(e) => setFuel(e.target.value)} placeholder="Material, e.g. PMMA" className="field min-w-[9.5rem] flex-1" />
          </div>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={() => ask()} />}

      {!result && !error && !loading && (
        <EmptyState icon="forum" title="Ask a question to get started">
          Pick a suggestion above or type your own. You will get a summary, the passages it was built from, and related experiments.
        </EmptyState>
      )}

      {result && <Answer result={result} dimmed={loading} />}
    </div>
  );
}

function Pill({ dot, children }: { dot: string; children: React.ReactNode }) {
  return (
    <div className="t-code flex items-center gap-space-sm rounded-lg bg-surface-container-high px-space-md py-space-xs font-semibold text-on-surface shadow-md">
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {children}
    </div>
  );
}

function Answer({ result, dimmed }: { result: AssistantResponse; dimmed: boolean }) {
  const openProvenance = useProvenance();
  const interp = result.generated_interpretation;
  const usedModel = interp.synthesis_mode === "external_llm_grounded";
  const sources = result.published_scientific_evidence;
  const runs = result.structured_sql_experiments;

  return (
    <div className={`flex flex-col gap-space-lg transition-opacity ${dimmed ? "opacity-50" : ""}`}>
      <article
        className="relative overflow-hidden rounded-xl p-space-lg shadow-2xl md:p-space-xl"
        style={{ background: "linear-gradient(135deg, rgba(14, 22, 48, 0.85), rgba(9, 14, 30, 0.95))", border: "1px solid rgba(123, 208, 255, 0.18)" }}
      >
        <div className="mb-space-lg flex flex-wrap items-center justify-between gap-space-md border-b border-secondary/15 pb-space-lg">
          <div className="flex items-center gap-space-md">
            <span className="relative flex h-3 w-3">
              <span className="relative inline-flex h-3 w-3 rounded-full bg-secondary-container" />
            </span>
            <div>
              <div className="flex flex-wrap items-center gap-space-sm">
                <h2 className="t-title font-semibold tracking-tight text-on-surface">FLARE Copilot Summary</h2>
                <span className="t-label rounded-full border border-secondary/20 bg-secondary-container/15 px-space-sm py-0.5 text-secondary">
                  {usedModel ? "Written by an AI model" : "Assembled from sources (no AI model connected)"}
                </span>
              </div>
              <p className="t-code mt-0.5 text-on-surface-variant">AI-generated summary. Check the sources below before relying on it.</p>
            </div>
          </div>
          <CopyButton text={interp.markdown_content} />
        </div>
        <p className="t-label mb-space-md tracking-wider text-outline">You asked: {result.question}</p>
        <Markdown text={interp.markdown_content} />
      </article>

      <section className="flex flex-col gap-space-md">
        <div className="flex flex-wrap items-center justify-between gap-space-sm">
          <div className="flex items-center gap-space-sm">
            <Icon name="menu_book" className="text-secondary" />
            <h2 className="t-headline-md text-on-surface">Sources</h2>
          </div>
          <span className="t-code text-on-surface-variant">
            {sources.length} {sources.length === 1 ? "passage" : "passages"} from the FLARE knowledge base
          </span>
        </div>
        {sources.length === 0 ? (
          <EmptyState icon="search_off" title="No matching passages">
            Nothing in the knowledge base matched this question with the current filters.
          </EmptyState>
        ) : (
          <div className="grid grid-cols-1 gap-space-md md:grid-cols-2 xl:grid-cols-3">
            {sources.map((s, i) => {
              const tone = SOURCE_TONES[i % SOURCE_TONES.length];
              return (
                <div key={s.chunk_id} className="flex flex-col justify-between rounded-xl p-space-lg shadow-lg transition-transform duration-200 hover:-translate-y-1" style={{ background: "linear-gradient(160deg, rgba(15, 23, 50, 0.75), rgba(8, 13, 28, 0.85))", border: `1px solid ${tone.border}` }}>
                  <div className="flex flex-col gap-space-md">
                    <div className="flex items-center justify-between gap-space-sm">
                      <span className={`t-code rounded-full border px-space-sm py-1 font-semibold ${tone.chip}`}>
                        [{i + 1}] {s.external_investigation_id}
                      </span>
                      <span className="flex gap-1">
                        <DomainChip domain={s.combustion_domain} />
                        <GravityChip gravity={s.gravity_regime} />
                      </span>
                    </div>
                    <h3 className="t-title font-semibold leading-snug text-on-surface">{s.section_title}</h3>
                    <p className={`t-body line-clamp-6 border-l-2 pl-space-sm leading-relaxed text-on-surface-variant ${tone.rule}`}>{s.content_text}</p>
                  </div>
                  <div className="mt-space-md flex flex-col gap-space-xs border-t border-white/5 pt-space-md">
                    <span className="t-code line-clamp-2 text-outline">
                      {s.document_title}
                      {s.publication_year ? ` (${s.publication_year})` : ""}
                    </span>
                    <a href={s.doi ? doiUrl(s.doi) : s.source_url} target="_blank" rel="noreferrer" className={`t-code inline-flex items-center gap-1.5 font-medium hover:underline ${tone.link}`}>
                      {s.doi ? `DOI ${s.doi}` : "Open source archive"}
                      <Icon name="open_in_new" size={14} />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <Accordion
        title="Related experiments"
        badge={
          <span className="t-code rounded-full bg-surface-container-highest px-space-md py-space-xs text-secondary">
            {runs.length} {runs.length === 1 ? "run" : "runs"}
          </span>
        }
        hint="From the experiment database"
      >
        <div className="grid grid-cols-1 gap-space-sm pt-space-sm md:grid-cols-2 xl:grid-cols-3">
          {runs.map((r) => (
            <div key={r.run_id} className="flex flex-col justify-between gap-space-md rounded-lg bg-surface-container-lowest p-space-md shadow-inner">
              <div className="flex flex-col gap-space-xs">
                <div className="flex items-center justify-between gap-space-sm">
                  <span className="t-title text-on-surface">{r.run_code}</span>
                  <DomainChip domain={r.combustion_domain} />
                </div>
                <p className="t-code text-on-surface-variant">{r.fuel_material}</p>
                <dl className="t-code mt-space-xs flex flex-col gap-1 text-outline">
                  <Line label="O₂">{r.oxygen_fraction !== null ? pct(r.oxygen_fraction) : <NotRecorded />}</Line>
                  <Line label="Pressure">{r.pressure_normalized_kpa !== null ? `${num(r.pressure_normalized_kpa, 1)} kPa` : <NotRecorded />}</Line>
                  <Line label="Airflow">{r.flow_velocity_normalized_cm_s !== null ? `${num(r.flow_velocity_normalized_cm_s, 1)} cm/s` : <NotRecorded reason={r.flow_velocity_missing_reason} />}</Line>
                  {r.measurements.map((m) => (
                    <Line key={m.id} label={fieldLabel(m.canonical_field)}>
                      {m.normalized_value !== null ? `${num(m.normalized_value, 3)} ${m.normalized_unit ?? ""}` : <NotRecorded reason={m.missing_reason} />}
                    </Line>
                  ))}
                </dl>
              </div>
              <div className="flex items-center justify-between pt-space-xs">
                <span className="t-label text-secondary">
                  {r.external_investigation_id} · <GravityLabel earth={r.is_terrestrial_baseline} />
                </span>
                <button type="button" onClick={() => openProvenance(r.run_code)} title="Where this data comes from" aria-label={`Source details for ${r.run_code}`} className="text-on-surface-variant hover:text-on-surface">
                  <Icon name="visibility" size={18} />
                </button>
              </div>
            </div>
          ))}
        </div>
      </Accordion>

      <Accordion title="How this answer was found" iconClass="text-outline" hint="Search steps">
        <ol className="flex flex-col gap-space-sm pt-space-xs">
          {result.retrieval_pipeline_trace.map((step) => (
            <li key={step.step} className="tile p-space-sm">
              <div className="t-code font-semibold text-secondary">{step.step}</div>
              <p className="t-body text-on-surface-variant">{step.detail}</p>
            </li>
          ))}
        </ol>
      </Accordion>

      <p className="t-code text-outline">{result.scientific_disclaimer}</p>
    </div>
  );
}

function Line({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-space-md">
      <dt>{label}</dt>
      <dd className="text-right text-on-surface">{children}</dd>
    </div>
  );
}

function GravityLabel({ earth }: { earth: boolean }) {
  return <span className={earth ? "text-tertiary" : "text-secondary"}>{earth ? "Earth 1g" : "Space"}</span>;
}
