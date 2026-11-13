from typing import Any, Dict, List, Optional
import httpx
import numpy as np
from sqlalchemy.orm import Session

from .config import GEMINI_API_KEY, LLM_MODEL, OPENAI_API_KEY, SCIENTIFIC_DISCLAIMER
from .ingestion import compute_text_embedding
from .models import ExperimentRun, Investigation, KnowledgeChunk, KnowledgeDocument
from .schemas import AssistantQueryRequest


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


def call_external_llm_if_available(
    question: str,
    evidence_chunks: List[Dict[str, Any]],
    sql_runs: List[Dict[str, Any]],
) -> Optional[str]:
    """
    Attempt to call Gemini or OpenAI API with strict source-grounding instructions.
    Returns None if no valid external key or if the endpoint is unreachable, triggering deterministic synthesis.
    """
    evidence_text = "\n\n".join(
        f"[{c['external_investigation_id']} | DOI: {c['doi'] or 'Archive-Link'}] ({c['section_title']}): {c['content_text']}"
        for c in evidence_chunks
    )
    runs_text = "\n".join(
        f"- Run {r['run_code']} ({r['external_investigation_id']}, domain={r['combustion_domain']}, gravity={r['gravity_regime']}, "
        f"fuel={r['fuel_material']}, O2={r['oxygen_fraction']}, P={r['pressure_normalized_kpa']} kPa, "
        f"V_air={r['flow_velocity_normalized_cm_s']} cm/s): "
        + ", ".join(
            f"{m['canonical_field']}={m['normalized_value']} {m['normalized_unit']}"
            if m["value_status"] == "measured"
            else f"{m['canonical_field']}=MISSING({m['missing_reason']})"
            for m in r["measurements"]
        )
        for r in sql_runs
    )

    system_prompt = (
        "You are the FLARE AI Scientific Research Assistant for the NASA Space Apps Challenge 2026 (Flame in Freefall). "
        "Synthesize an explanation answering the user's question strictly using the provided NASA PSI, JAXA DARTS, and FSRI "
        "evidence chunks and PostgreSQL experiment records. Cite every claim with [PSI-XX, DOI] or [JAXA-GC]. "
        "Explicitly distinguish microgravity (0g) behavior from normal-gravity (1g) baseline data, respect combustion domain "
        "boundaries (solid vs gas vs liquid_droplet vs aerosol_smoke), and mention any missing measurement flags."
    )
    user_prompt = f"Question: {question}\n\nPublished Evidence Chunks:\n{evidence_text}\n\nStructured SQL Experiments:\n{runs_text}"

    # Try Gemini API if key is set and looks like a standard AIza key or Vertex key
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent?key={GEMINI_API_KEY}"
            payload = {
                "systemInstruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 700},
            }
            with httpx.Client(timeout=6.0) as client:
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                    if parts and parts[0].get("text"):
                        return parts[0]["text"].strip()
        except Exception:
            pass

    if OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.15,
            }
            with httpx.Client(timeout=6.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"].strip()
        except Exception:
            pass

    return None


def build_deterministic_grounded_synthesis(
    question: str,
    evidence_chunks: List[Dict[str, Any]],
    sql_runs: List[Dict[str, Any]],
) -> str:
    """
    Build a rigorous, citation-grounded scientific interpretation directly from the retrieved
    Knowledge Base chunks and PostgreSQL structured experiment runs.
    """
    lines: List[str] = []
    lines.append("### Source-Grounded Scientific Synthesis (Generated Interpretation)")
    lines.append(
        f"Based on hybrid retrieval across **{len(evidence_chunks)} peer-reviewed / repository evidence chunks** and "
        f"**{len(sql_runs)} structured PostgreSQL experiment records**, the key mechanisms addressing your query are:"
    )

    for idx, ch in enumerate(evidence_chunks[:3], start=1):
        cite = f"[{ch['external_investigation_id']}" + (f" | DOI: {ch['doi']}]" if ch.get("doi") else " | Archive Link]")
        lines.append(
            f"{idx}. **{ch['section_title']} ({ch['combustion_domain']} / {ch['gravity_regime']})** {cite}: "
            f"{ch['content_text']}"
        )

    if sql_runs:
        lines.append("\n### Quantitative Evidence from Structured Experiment Runs (PostgreSQL)")
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

    lines.append(
        "\n### Domain & Gravity Guardrail Note\n"
        "- Microgravity ($0g$) transport is governed by molecular diffusion and low-velocity spacecraft ventilation "
        "($1\\text{--}20\\text{ cm/s}$), whereas terrestrial ($1g$) FSRI baseline measurements involve buoyant plume "
        "convection ($45\\text{--}55\\text{ cm/s}$) and are isolated from $0g$ rankings."
    )
    return "\n".join(lines)


def run_hybrid_assistant_query(db: Session, req: AssistantQueryRequest) -> Dict[str, Any]:
    """
    Execute the Hybrid Knowledge Architecture Retrieval Pipeline:
    1. Semantic Vector Search (64-dim cosine similarity over KnowledgeChunk.embedding_json)
    2. Keyword Lexical Matching (scientific terms, fuels, investigation IDs)
    3. Structured SQL Query over PostgreSQL/DB (ExperimentRun + Measurement + Investigation)
    4. Domain & Gravity Regime Validation
    5. Source-Grounded Synthesis with strict separation between Published Evidence & Generated Interpretation
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

        scored_chunks.append({
            "chunk_id": ch.id,
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

    # Step 3: Structured SQL Query over ExperimentRun & Measurement
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

    # Step 4: LLM Synthesis with Deterministic Citation-Grounded Fallback
    llm_text = call_external_llm_if_available(req.question, top_chunks, top_runs)
    synthesis_mode = "external_llm_grounded" if llm_text else "deterministic_citation_grounded_engine"
    if not llm_text:
        llm_text = build_deterministic_grounded_synthesis(req.question, top_chunks, top_runs)

    return {
        "question": req.question,
        "scientific_disclaimer": SCIENTIFIC_DISCLAIMER,
        "retrieval_pipeline_trace": [
            {
                "step": "1. Semantic Vector Search (pgvector / 64-dim Cosine Similarity)",
                "detail": f"Evaluated {len(all_chunks)} embedded scientific document chunks; top semantic score = {top_chunks[0]['semantic_score'] if top_chunks else 0.0}.",
            },
            {
                "step": "2. Keyword & Metadata Lexical Match",
                "detail": f"Combined semantic (65%) + keyword (35%) hybrid score across section titles, fuel tags, and DOIs.",
            },
            {
                "step": "3. Structured PostgreSQL Query (ExperimentRun + Measurement)",
                "detail": f"Retrieved {len(top_runs)} matching experiment runs preserving original/normalized units and explicit missing_reason flags.",
            },
            {
                "step": "4. Scientific Guardrails & Provenance Separation",
                "detail": "Published repository facts and structured measurements are strictly separated from the generated interpretation below.",
            },
        ],
        "published_scientific_evidence": top_chunks,
        "structured_sql_experiments": top_runs,
        "generated_interpretation": {
            "label": "AI-Synthesized Scientific Interpretation (Derived from Retrieved Sources — Verify Against Primary DOIs)",
            "synthesis_mode": synthesis_mode,
            "markdown_content": llm_text,
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
        },
    }
