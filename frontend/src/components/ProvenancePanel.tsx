"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { doiUrl, fieldLabel, num, shortHash } from "@/lib/format";
import { useAsync } from "@/lib/hooks";
import { ProvenanceRecord } from "@/lib/types";
import { CopyButton, ErrorState, Icon, Loading } from "./ui";

const ProvenanceContext = createContext<(recordId: string) => void>(() => {});

/** Returns a function that opens the "Where this data comes from" panel for a run code or study code. */
export const useProvenance = () => useContext(ProvenanceContext);

export function ProvenanceProvider({ children }: { children: React.ReactNode }) {
  const [recordId, setRecordId] = useState<string | null>(null);
  const open = useCallback((id: string) => setRecordId(id), []);

  useEffect(() => {
    if (!recordId) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setRecordId(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [recordId]);

  return (
    <ProvenanceContext.Provider value={open}>
      {children}
      {recordId && <Panel recordId={recordId} onClose={() => setRecordId(null)} />}
    </ProvenanceContext.Provider>
  );
}

function Section({ icon, title, children }: { icon: string; title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-space-sm">
      <h3 className="t-label flex items-center gap-1.5 tracking-wider text-secondary">
        <Icon name={icon} size={16} />
        {title}
      </h3>
      <div className="tile flex flex-col gap-space-sm p-space-md">{children}</div>
    </section>
  );
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-space-md">
      <span className="t-code shrink-0 text-outline">{label}</span>
      <span className="t-body text-right text-on-surface">{children}</span>
    </div>
  );
}

function Panel({ recordId, onClose }: { recordId: string; onClose: () => void }) {
  const { data, error, loading, reload } = useAsync(() => api.provenance(recordId), [recordId]);

  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label="Where this data comes from">
      <button type="button" aria-label="Close panel" className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div
        className="relative flex h-full w-full max-w-md flex-col gap-space-lg overflow-y-auto p-space-lg shadow-2xl"
        style={{ background: "rgba(10, 16, 36, 0.97)", borderLeft: "1px solid rgba(123, 208, 255, 0.2)" }}
      >
        <div className="flex items-start justify-between gap-space-md">
          <div>
            <h2 className="t-headline-md text-on-surface">Where this data comes from</h2>
            <span className="t-code mt-1 inline-block rounded bg-surface-container-high px-space-sm py-0.5 text-secondary">{recordId}</span>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-lg p-1.5 text-on-surface-variant hover:bg-surface-container-high hover:text-on-surface">
            <Icon name="close" />
          </button>
        </div>

        {loading && <Loading label="Tracing the source…" />}
        {error && !loading && <ErrorState message={error} onRetry={reload} />}
        {data && !loading && !error && <Body record={data} />}
      </div>
    </div>
  );
}

function Body({ record }: { record: ProvenanceRecord }) {
  // Run records nest the study and publisher; study records carry them at the top level.
  const study = record.investigation ?? {
    external_id: record.external_id ?? null,
    title: record.title ?? null,
    doi: record.doi ?? null,
    version: record.version ?? null,
    source_url: record.source_url ?? null,
  };
  const publisher = record.source_publisher ?? {
    publisher: record.publisher ?? null,
    source_name: null,
    license: record.license ?? null,
    access_date: null,
    citation_text: record.citation_text ?? null,
  };
  const files = record.source_files ?? [];
  const mappings = record.field_mappings_applied ?? [];
  const derived = record.derived_audit_trail ?? [];

  return (
    <>
      <Section icon="science" title="Study">
        <div className="t-title text-on-surface">{study.title ?? "—"}</div>
        <Row label="Code">{study.external_id ?? "—"}</Row>
        {study.version && <Row label="Version">{study.version}</Row>}
        <Row label="DOI">
          {study.doi ? (
            <a href={doiUrl(study.doi)} target="_blank" rel="noreferrer" className="text-secondary hover:underline">
              {study.doi}
            </a>
          ) : (
            <span className="text-on-surface-variant">None listed</span>
          )}
        </Row>
        {study.source_url && (
          <a href={study.source_url} target="_blank" rel="noreferrer" className="t-code inline-flex items-center gap-1 text-secondary hover:underline">
            Open the original record
            <Icon name="open_in_new" size={14} />
          </a>
        )}
      </Section>

      <Section icon="account_balance" title="Source organisation">
        <div className="t-title text-on-surface">{publisher.publisher ?? "—"}</div>
        {publisher.source_name && <p className="t-body text-on-surface-variant">{publisher.source_name}</p>}
        {publisher.license && <Row label="Licence">{publisher.license}</Row>}
        {publisher.access_date && <Row label="Accessed">{publisher.access_date}</Row>}
        {publisher.citation_text && <p className="t-code leading-relaxed text-outline">{publisher.citation_text}</p>}
      </Section>

      <Section icon="description" title={files.length === 1 ? "Original file" : "Original files"}>
        {files.length === 0 && <p className="t-body text-on-surface-variant">No files are registered for this record.</p>}
        {files.map((f) => (
          <div key={`${f.file_name}-${f.version}`} className="flex flex-col gap-1.5">
            <div className="t-title break-all text-on-surface">{f.file_name}</div>
            <div className="flex flex-wrap items-center justify-between gap-space-sm">
              <span className="t-code text-on-surface-variant" title={f.checksum_sha256}>
                Fingerprint (SHA-256): <span className="text-secondary">{shortHash(f.checksum_sha256)}</span>
              </span>
              <CopyButton text={f.checksum_sha256} />
            </div>
            <span className="t-code text-outline">Version {f.version}</span>
          </div>
        ))}
      </Section>

      {mappings.length > 0 && (
        <Section icon="tune" title="Unit conversions used for this source">
          {mappings.map((m, i) => (
            <div key={i} className="flex flex-col gap-0.5">
              <div className="flex items-center justify-between gap-space-sm">
                <span className="t-body text-on-surface">{fieldLabel(m.canonical_field)}</span>
                <span className="t-code text-secondary">
                  {m.source_unit} → {m.canonical_unit}
                </span>
              </div>
              <p className="t-code text-outline">{m.transform_description}</p>
            </div>
          ))}
        </Section>
      )}

      {derived.length > 0 && (
        <Section icon="calculate" title="Calculated values">
          {derived.map((d) => (
            <div key={d.id} className="flex flex-col gap-0.5">
              <div className="flex items-baseline justify-between gap-space-sm">
                <span className="t-body text-on-surface">{d.result_name}</span>
                <span className="t-title text-tertiary">
                  {num(d.result_value, 4)} <span className="t-code text-outline">{d.result_unit}</span>
                </span>
              </div>
              <p className="t-code text-outline">{d.explanation}</p>
            </div>
          ))}
        </Section>
      )}
    </>
  );
}
