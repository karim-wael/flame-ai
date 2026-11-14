"""
FLARE AI - adapter between the data contract (v0.3) and the LLM engine.

Reads:   processed/corpus_chunks.jsonl   (NASA document text, from Data Eng.)
         processed/coverage.csv          (COV-* / GAP-* coverage matrix)
Outputs: chunk dicts in the shape flare_llm_engine.generate_flare_response expects.

Karim owns real retrieval. Until his search is ready, `keyword_retrieve` is a
stand-in so you can test end to end. Swap it for his function; nothing else changes.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

try:
    from .flare_llm_engine import generate_flare_response
except ImportError:
    from flare_llm_engine import generate_flare_response

PARTIAL_G = re.compile(
    r"\b(partial[\s-]?gravity|lunar|moon|mars|martian|0\.16\s?g|0\.38\s?g|reduced gravity)\b",
    re.I,
)
GAP_WORDS = re.compile(r"\b(gap|untested|not tested|no data|coverage|covered)\b", re.I)


def corpus_row_to_chunk(row: dict[str, Any]) -> dict[str, Any]:
    """corpus_chunks.jsonl row -> engine chunk. The cite id is chunk_id, because
    source_id (e.g. PSI-25) is shared by many chunks and would be ambiguous."""
    doi = row.get("doi") or None
    title = row.get("doc_title") or row["chunk_id"]
    if row.get("section"):
        title = f'{title} - {row["section"]}'
    return {
        "source_id": row["chunk_id"],
        "title": title,
        "text": row["text"],
        "url": f"https://doi.org/{doi}" if doi else None,
        "investigation": row.get("source_id"),
        "doi": doi,
        "page_start": row.get("page_start"),
        "page_end": row.get("page_end"),
        "section": row.get("section"),
    }


def load_corpus(path: str | Path) -> list[dict[str, Any]]:
    chunks = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(corpus_row_to_chunk(json.loads(line)))
    return chunks


def load_coverage_chunks(path: str | Path) -> list[dict[str, Any]]:
    """coverage.csv row -> a pseudo-source the LLM can cite (COV-xx / GAP-xx).
    Built from the processed data, so it is labelled as such, not as NASA text."""
    out = []
    with open(path, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            text = (
                f'Coverage cell {r["cell_id"]}: gravity_regime={r["gravity_regime"]}; '
                f'domain={r["domain"]}; o2_band={r["o2_band"]}; '
                f'pressure_band={r["pressure_band"]}; flow_band={r["flow_band"]}; '
                f'total_runs={r["total_runs"]}; unique_runs={r["unique_runs"]}; '
                f'sources={r["sources"] or "none"}; coverage_status={r["coverage_status"]}. '
                f'{r["gap_note"]}'
            )
            out.append(
                {
                    "source_id": r["cell_id"],
                    "title": "FLARE coverage matrix (derived from processed NASA PSI runs)",
                    "text": text,
                    "url": None,
                    "investigation": None,
                    "doi": None,
                    "page_start": None,
                    "page_end": None,
                    "section": None,
                    "_cov_status": r["coverage_status"],
                    "_cov_gravity": r["gravity_regime"],
                }
            )
    return out


def select_coverage_chunks(query: str, cov: list[dict[str, Any]], k: int = 4) -> list[dict[str, Any]]:
    """Add coverage cells only when the question is about gaps or partial gravity."""
    if PARTIAL_G.search(query):
        picked = [c for c in cov if c["_cov_gravity"] == "partial_gravity" or c["_cov_status"] == "gap"]
        return picked[:k]
    if GAP_WORDS.search(query):
        return [c for c in cov if c["_cov_status"] != "covered"][:k]
    return []


def keyword_retrieve(query: str, chunks: list[dict[str, Any]], k: int = 6) -> list[dict[str, Any]]:
    """Stand-in for Karim's retrieval. Plain word overlap, nothing smart."""
    words = set(re.findall(r"[a-z0-9]+", query.lower()))
    def score(c: dict[str, Any]) -> int:
        return len(words & set(re.findall(r"[a-z0-9]+", c["text"].lower())))
    return [c for c in sorted(chunks, key=score, reverse=True)[:k] if score(c) > 0]


def answer(query: str, corpus: list[dict], coverage: list[dict], retrieve=keyword_retrieve, **kw):
    """retrieve(query, corpus) -> list of chunks. Replace with Karim's retriever."""
    chunks = retrieve(query, corpus) + select_coverage_chunks(query, coverage)
    # drop internal helper keys before they reach the engine
    clean = [{k: v for k, v in c.items() if not k.startswith("_")} for c in chunks]
    return generate_flare_response(query, clean, **kw)


if __name__ == "__main__":
    # Test on the lightweight fixtures first, then switch to processed/.
    base = Path("FLARE_AI_Data_Handoff/fixtures")
    corpus = load_corpus(base / "corpus_chunks.jsonl")
    coverage = load_coverage_chunks(base / "coverage.csv")
    for q in [
        "What do we know about flame spread at low oxygen in microgravity?",
        "Can you tell me what fire does on the Moon?",
    ]:
        print(json.dumps(answer(q, corpus, coverage, provider="gemini"), indent=2))

