from typing import Any, Dict, List, Optional
import os
import re
import numpy as np
from sqlalchemy.orm import Session

from .config import GEMINI_API_KEY, HANDOFF_DIR, LLM_MODEL, OPENAI_API_KEY, SCIENTIFIC_DISCLAIMER
from .flare_llm_adapter import load_coverage_chunks, select_coverage_chunks
from .flare_llm_engine import (
    DISCLAIMER as FLARE_LLM_DISCLAIMER,
    FlareResponse,
    LLMCitation,
    LLMOutput,
    _PARTIAL_G,
    _verify_and_enrich,
    generate_flare_response,
)
from .ingestion import compute_text_embedding
from .models import ExperimentRun, Investigation, KnowledgeChunk, KnowledgeDocument
from .schemas import AssistantQueryRequest


_COVERAGE_CACHE: Optional[List[Dict[str, Any]]] = None


def get_coverage_chunks() -> List[Dict[str, Any]]:
    global _COVERAGE_CACHE
    if _COVERAGE_CACHE is None:
        cov_path = HANDOFF_DIR / "processed" / "coverage.csv"
        if cov_path.exists():
            _COVERAGE_CACHE = load_coverage_chunks(cov_path)
        else:
            _COVERAGE_CACHE = []
    return _COVERAGE_CACHE


def cosine_sim(vec_a: List[float], vec_b: List[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    a = np.array(vec_a, dtype=float)
    b = np.array(vec_b, dtype=float)
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def keyword_overlap_score(query: str, chunk: KnowledgeChunk) -> float:
    q_tokens = {
        t.strip(".,;:?!()[]\"'").lower()
        for t in query.split()
        if len(t.strip(".,;:?!()[]\"'")) > 2
    }
    if not q_tokens:
        return 0.0
    haystack = (
        f"{chunk.section_title} {chunk.content_text} "
        + " ".join(chunk.keywords or [])
        + " "
        + " ".join(chunk.fuel_tags or [])
    ).lower()
    hits = sum(1 for tok in q_tokens if tok in haystack)
    return min(1.0, hits / max(1, len(q_tokens)))


def _extract_verbatim_quote(text: str, max_words: int = 20) -> str:
    words = text.strip().split()
    return " ".join(words[:max_words])


def build_deterministic_flare_output(
    question: str,
    engine_chunks: List[Dict[str, Any]],
    sql_runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Build a guardrail-compliant FlareResponse (using Farah's LLMOutput + _verify_and_enrich)
    when external LLM APIs are offline or unreachable.
    """
    is_partial_g = bool(_PARTIAL_G.search(question))
    citations_in: List[LLMCitation] = []
    answer_parts: List[str] = []

    if is_partial_g:
        cov_ids = [c["source_id"] for c in engine_chunks if str(c["source_id"]).startswith(("GAP-", "COV-"))]
        cov_ref = f" [{cov_ids[0]}]" if cov_ids else ""
        answer_parts.append(
            f"Partial-gravity combustion (Lunar ~0.16 g, Martian ~0.38 g, or intermediate gravity between 0 g and 1 g) "
            f"is an open research gap with no validated NASA PSI partial-gravity experiment records in this archive{cov_ref}. "
            f"FLARE AI treats microgravity (0 g) and normal gravity (1 g) as bounding regimes rather than interpolating between them."
        )

    for ch in engine_chunks[:4]:
        cid = str(ch["source_id"])
        quote = _extract_verbatim_quote(ch["text"], max_words=20)
        if quote:
            citations_in.append(LLMCitation(source_id=cid, quote=quote))
        snippet = ch["text"].strip()
        if len(snippet) > 220:
            snippet = snippet[:217].rsplit(" ", 1)[0] + "..."
        answer_parts.append(f"{ch.get('title') or cid} reports: {snippet} [{cid}].")

    missing_info: List[str] = []
    if is_partial_g:
        missing_info.append("Validated partial-gravity (Lunar 0.16 g / Martian 0.38 g) combustion test runs in NASA PSI.")
    for r in sql_runs[:3]:
        for m in r["measurements"]:
            if m["value_status"] != "measured":
                missing_info.append(
                    f"Run {r['run_code']} ({r['external_investigation_id']}): {m['canonical_field']} is {m['missing_reason']}."
                )
    if not missing_info:
        missing_info.append("Direct target-condition match for unmeasured environmental parameters outside the retrieved PSI runs.")

    uncertainty = (
        "Retrieved NASA PSI records bound the query within their tested microgravity (0 g) and ground baseline (1 g) conditions; "
        "SPICE, SAME, and SAME-R do not report ambient oxygen or pressure in the archive, and terrestrial 1 g behavior does not transfer directly to microgravity."
    )
    if is_partial_g:
        uncertainty = (
            "No partial-gravity (0.16 g Lunar or 0.38 g Martian) data exist in the archive (see GAP cells); "
            + uncertainty
        )

    out = LLMOutput(
        status="answered" if engine_chunks else "insufficient_context",
        answer_text=" ".join(answer_parts),
        uncertainty_statement=uncertainty,
        missing_information=missing_info[:5],
        partial_gravity_gap_noted=is_partial_g,
        citations=citations_in,
    )
    verified_citations, flags = _verify_and_enrich(out, engine_chunks)
    return FlareResponse(
        status=out.status,
        answer_text=out.answer_text,
        uncertainty_statement=out.uncertainty_statement,
        missing_information=out.missing_information,
        partial_gravity_gap_noted=out.partial_gravity_gap_noted,
        citations=verified_citations,
        guardrail_flags=flags,
        disclaimer=FLARE_LLM_DISCLAIMER,
        model="deterministic-guardrail-synthesizer",
    ).model_dump()


def format_flare_response_as_markdown(
    flare_resp: Dict[str, Any],
    sql_runs: List[Dict[str, Any]],
) -> str:
    lines: List[str] = []
    lines.append("### Source-Grounded Scientific Synthesis")
    if flare_resp.get("partial_gravity_gap_noted"):
        lines.append(
            "> **Partial-Gravity Guardrail (G2):** Partial-gravity combustion (Lunar ~0.16 g / Martian ~0.38 g) "
            "is an open gap in the NASA PSI archive. 0 g and 1 g records below serve only as bounding regimes.\n"
        )
    lines.append(flare_resp.get("answer_text", ""))

    if flare_resp.get("uncertainty_statement"):
        lines.append(f"\n### Uncertainty & Condition Mismatches\n{flare_resp['uncertainty_statement']}")

    missing = flare_resp.get("missing_information") or []
    if missing:
        lines.append("\n### Missing Information & Archive Gaps")
        for item in missing:
            lines.append(f"- {item}")

    cits = flare_resp.get("citations") or []
    if cits:
        lines.append("\n### Verbatim Source Citations")
        for c in cits:
            badge = "Verified verbatim" if c.get("verified") else "Unverified excerpt"
            lines.append(f'- **`[{c["source_id"]}]`** (*{badge}*): "{c["quote"]}"')

    if sql_runs:
        lines.append("\n### Quantitative Evidence from Structured Experiment Runs")
        for r in sql_runs[:4]:
            meas_parts = []
            for m in r["measurements"]:
                if m["value_status"] == "measured" and m["normalized_value"] is not None:
                    meas_parts.append(f"`{m['canonical_field']} = {m['normalized_value']} {m['normalized_unit']}`")
                else:
                    meas_parts.append(f"`{m['canonical_field']} = NULL (missing_reason: {m['missing_reason']})`")
            meas_summary = ", ".join(meas_parts) if meas_parts else "context metadata only"
            flow_str = (
                f"{r['flow_velocity_normalized_cm_s']} cm/s"
                if r["flow_velocity_normalized_cm_s"] is not None
                else f"NULL ({r.get('flow_velocity_missing_reason') or 'unavailable_in_source'})"
            )
            lines.append(
                f"- **`{r['run_code']}`** (*{r['external_investigation_id']}*, `{r['fuel_material']}`, "
                f"`{r['combustion_domain']}`, `{r['gravity_regime']}`, "
                f"$O_2 = {r['oxygen_fraction']}$, $P = {r['pressure_normalized_kpa']}\\text{{ kPa}}$, "
                f"$V_{{\\text{{air}}}} = \\text{{{flow_str}}}$): {meas_summary}."
            )

    return "\n".join(lines)


def run_hybrid_assistant_query(db: Session, req: AssistantQueryRequest) -> Dict[str, Any]:
    """
    Execute the Hybrid Knowledge Architecture Retrieval Pipeline + Farah's LLM & Guardrail Engine:
    1. Semantic Vector Search (64-dim cosine similarity over KnowledgeChunk.embedding_json)
    2. Keyword Lexical Matching (scientific terms, fuels, investigation IDs)
    3. Coverage Matrix Selection (COV-* / GAP-* cells from processed/coverage.csv via flare_llm_adapter)
    4. Structured SQL Query over ExperimentRun + Measurement + Investigation
    5. Guardrail-Enforced Synthesis & Verbatim Quote Verification via flare_llm_engine
    """
    query_vec = compute_text_embedding(req.question)
    all_chunks: List[KnowledgeChunk] = db.query(KnowledgeChunk).all()

    scored_chunks: List[Dict[str, Any]] = []
    for ch in all_chunks:
        if req.combustion_domain and ch.combustion_domain != req.combustion_domain:
            continue
        if req.gravity_regime and ch.gravity_regime != req.gravity_regime:
            continue
        if req.fuel_filter:
            fuel_hay = (" ".join(ch.fuel_tags or []) + " " + ch.content_text).lower()
            if req.fuel_filter.lower() not in fuel_hay:
                continue

        doc: KnowledgeDocument = ch.document
        inv: Optional[Investigation] = doc.investigation if doc else None
        sem_score = cosine_sim(query_vec, ch.embedding_json or [])
        kw_score = keyword_overlap_score(req.question, ch)
        hybrid_score = round(0.65 * sem_score + 0.35 * kw_score, 4)

        cite_chunk_id = f"{inv.external_id if inv else 'PSI'}:c{ch.id}"
        scored_chunks.append({
            "chunk_id": ch.id,
            "cite_id": cite_chunk_id,
            "document_id": doc.id if doc else None,
            "document_title": doc.title if doc else "",
            "doc_type": doc.doc_type if doc else "pdf_report",
            "authors": doc.authors if doc else None,
            "publication_year": doc.publication_year if doc else None,
            "publisher": doc.source.publisher if (doc and doc.source) else "NASA PSI",
            "external_investigation_id": inv.external_id if inv else "UNKNOWN",
            "investigation_id": inv.id if inv else None,
            "doi": doc.doi if doc else None,
            "source_url": doc.source_url if doc else "",
            "section_title": ch.section_title,
            "content_text": ch.content_text,
            "combustion_domain": ch.combustion_domain,
            "gravity_regime": ch.gravity_regime,
            "fuel_tags": ch.fuel_tags,
            "keywords": ch.keywords,
            "semantic_score": round(sem_score, 4),
            "keyword_score": round(kw_score, 4),
            "hybrid_score": hybrid_score,
        })

    scored_chunks.sort(key=lambda x: x["hybrid_score"], reverse=True)
    top_chunks = scored_chunks[: req.top_k_chunks]

    # Step 3: Build engine chunks in the shape flare_llm_engine.generate_flare_response expects
    engine_chunks: List[Dict[str, Any]] = [
        {
            "source_id": c["cite_id"],
            "title": f"{c['document_title']} - {c['section_title']}" if c.get("section_title") else c["document_title"],
            "text": c["content_text"],
            "url": f"https://doi.org/{c['doi']}" if c.get("doi") else (c.get("source_url") or None),
            "investigation": c["external_investigation_id"],
            "doi": c.get("doi"),
            "page_start": None,
            "page_end": None,
            "section": c.get("section_title"),
        }
        for c in top_chunks
    ]

    # Add coverage matrix cells (COV-* / GAP-*) when query touches partial gravity or gaps
    cov_selected = select_coverage_chunks(req.question, get_coverage_chunks())
    for cov_c in cov_selected:
        engine_chunks.append({k: v for k, v in cov_c.items() if not k.startswith("_")})

    # Step 4: Structured SQL Query over ExperimentRun & Measurement
    matched_inv_ids = {c["investigation_id"] for c in top_chunks if c.get("investigation_id")}
    matched_domains = {c["combustion_domain"] for c in top_chunks}

    sql_query = db.query(ExperimentRun)
    if req.combustion_domain:
        sql_query = sql_query.filter(ExperimentRun.combustion_domain == req.combustion_domain)
    if req.gravity_regime:
        sql_query = sql_query.filter(ExperimentRun.gravity_regime == req.gravity_regime)

    candidate_runs: List[ExperimentRun] = sql_query.all()

    scored_runs: List[Dict[str, Any]] = []
    q_lower = req.question.lower()
    for r in candidate_runs:
        if req.fuel_filter and req.fuel_filter.lower() not in r.fuel_material.lower():
            continue
        inv = r.investigation
        relevance = 0.0
        if r.investigation_id in matched_inv_ids:
            relevance += 0.55
        if r.combustion_domain in matched_domains:
            relevance += 0.25
        if any(tok in r.fuel_material.lower() for tok in q_lower.split() if len(tok) > 3):
            relevance += 0.30
        if inv and inv.external_id.lower() in q_lower:
            relevance += 0.45

        scored_runs.append({
            "run_id": r.id,
            "run_code": r.run_code,
            "investigation_id": inv.id if inv else None,
            "external_investigation_id": inv.external_id if inv else "UNKNOWN",
            "investigation_title": inv.title if inv else "",
            "doi": inv.doi if inv else None,
            "source_url": inv.source_url if inv else "",
            "combustion_domain": r.combustion_domain,
            "gravity_regime": r.gravity_regime,
            "is_terrestrial_baseline": r.is_terrestrial_baseline,
            "platform": r.platform,
            "fuel_material": r.fuel_material,
            "oxygen_fraction": r.oxygen_fraction,
            "pressure_normalized_kpa": r.pressure_normalized_kpa,
            "flow_velocity_normalized_cm_s": r.flow_velocity_normalized_cm_s,
            "flow_velocity_missing_reason": r.flow_velocity_missing_reason,
            "sql_relevance_score": round(relevance, 3),
            "measurements": [
                {
                    "id": m.id,
                    "variable_name": m.variable_name,
                    "canonical_field": m.canonical_field,
                    "value_numeric": m.value_numeric,
                    "unit": m.unit,
                    "normalized_value": m.normalized_value,
                    "normalized_unit": m.normalized_unit,
                    "value_status": m.value_status,
                    "missing_reason": m.missing_reason,
                }
                for m in r.measurements
            ],
        })

    scored_runs.sort(key=lambda x: x["sql_relevance_score"], reverse=True)
    top_runs = scored_runs[: req.top_k_experiments]

    # Step 5: Call flare_llm_engine (Gemini or OpenAI), with deterministic guardrail fallback if offline
    flare_resp: Optional[Dict[str, Any]] = None
    used_external_llm = False

    if GEMINI_API_KEY:
        os.environ.setdefault("GEMINI_API_KEY", GEMINI_API_KEY)
        candidate = generate_flare_response(req.question, engine_chunks, provider="gemini", max_retries=0)
        if "llm_call_failed" not in candidate.get("guardrail_flags", []):
            flare_resp = candidate
            used_external_llm = True

    if flare_resp is None and OPENAI_API_KEY:
        os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)
        candidate = generate_flare_response(req.question, engine_chunks, provider="openai", max_retries=0)
        if "llm_call_failed" not in candidate.get("guardrail_flags", []):
            flare_resp = candidate
            used_external_llm = True

    if flare_resp is None:
        flare_resp = build_deterministic_flare_output(req.question, engine_chunks, top_runs)

    synthesis_mode = "external_llm_grounded" if used_external_llm else "deterministic_citation_grounded_engine"
    llm_markdown = format_flare_response_as_markdown(flare_resp, top_runs)

    return {
        "question": req.question,
        "scientific_disclaimer": SCIENTIFIC_DISCLAIMER,
        "retrieval_pipeline_trace": [
            {
                "step": "1. Semantic Vector Search (pgvector / 64-dim Cosine Similarity)",
                "detail": f"Evaluated {len(all_chunks)} embedded scientific document chunks; top semantic score = {top_chunks[0]['semantic_score'] if top_chunks else 0.0}.",
            },
            {
                "step": "2. Keyword & Coverage Matrix Match (flare_llm_adapter)",
                "detail": f"Combined semantic (65%) + keyword (35%) hybrid score and selected {len(cov_selected)} coverage/gap matrix cells (COV-*/GAP-*).",
            },
            {
                "step": "3. Structured PostgreSQL Query (ExperimentRun + Measurement)",
                "detail": f"Retrieved {len(top_runs)} matching experiment runs preserving original/normalized units and explicit missing_reason flags.",
            },
            {
                "step": "4. Scientific Guardrails & Verbatim Quote Verification (flare_llm_engine)",
                "detail": f"Validated response against G1-G7 and D1-D6 guardrails; verified {sum(1 for c in flare_resp.get('citations', []) if c.get('verified'))} verbatim quote citations.",
            },
        ],
        "published_scientific_evidence": top_chunks,
        "structured_sql_experiments": top_runs,
        "flare_llm_response": flare_resp,
        "generated_interpretation": {
            "label": "AI-Synthesized Scientific Interpretation (Derived from Retrieved Sources — Verify Against Primary DOIs)",
            "synthesis_mode": synthesis_mode,
            "markdown_content": llm_markdown,
            "status": flare_resp.get("status"),
            "answer_text": flare_resp.get("answer_text"),
            "uncertainty_statement": flare_resp.get("uncertainty_statement"),
            "missing_information": flare_resp.get("missing_information"),
            "partial_gravity_gap_noted": flare_resp.get("partial_gravity_gap_noted"),
            "guardrail_flags": flare_resp.get("guardrail_flags"),
            "citations": [
                {
                    "external_id": c["external_investigation_id"],
                    "title": c["document_title"],
                    "doi": c["doi"],
                    "source_url": c["source_url"],
                    "publisher": c["publisher"],
                }
                for c in top_chunks
            ],
            "verified_citations": flare_resp.get("citations", []),
        },
    }
