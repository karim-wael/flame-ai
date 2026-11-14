"""Stage 5: Build citation-ready chatbot text corpus (processed/corpus_chunks.jsonl).

Follows etl/contract/DATA_CONTRACT.md Section 9:
  - chunk_id: {source_id}:{doc_slug}:p{page}:c{n}
  - source_id, doc_title, doc_file, doc_sha256, page_start, page_end,
    section, text, char_count, license, doi
  - Target chunk size: ~800-1,200 chars with ~150-char overlap, never crossing
    document boundaries.
"""
from __future__ import annotations

import csv
import json
import logging
import re
import zipfile
from pathlib import Path

import docx
import pypdf
import pptx

from .common import ROOT

logging.getLogger("pypdf").setLevel(logging.ERROR)

TARGET_MIN = 800
TARGET_MAX = 1150
OVERLAP = 150

DOC_TITLES = {
    "PSI-69_FLEX/FLEX DoD.docx": "FLEX Definition of Data (DoD)",
    "PSI-69_FLEX/FLEX Engineering Requirements Document.pdf": "FLEX Engineering Requirements Document (ERD)",
    "PSI-69_FLEX/FLEX Overall Ext File-2.pdf": "FLEX Overall Extinguishment & Operations Summary",
    "PSI-69_FLEX/FLEX_EIRD_v4.pdf": "FLEX Experiment Integration Requirements Document (EIRD v4)",
    "PSI-69_FLEX/FLEX_Test_Plan.pdf": "FLEX Science Test Plan",
    "PSI-69_FLEX/20CAL13_Readme.txt": "FLEX 20CAL13 Raw Data Readme",
    "PSI-69_FLEX/PSI-69_metadata_PSI-133_FLEX.zip": "PSI-69 FLEX Investigation Metadata (ISA-Tab i_Investigation.txt)",
    "PSI-25_BASS-II/BASS-2 Engineering Requirements.pptx": "BASS-II Engineering Requirements Presentation",
    "PSI-25_BASS-II/BASS-II data FAQ.docx": "BASS-II Data Frequently Asked Questions (FAQ)",
    "PSI-25_BASS-II/BASS-II Procedure.docx": "BASS-II Crew Operations Procedure",
    "PSI-25_BASS-II/BASS-II Summary Report.pdf": "BASS-II Experiment Summary Report",
    "PSI-25_BASS-II/SRD_BASS-II.pdf": "BASS-II Science Requirements Document (SRD)",
    "PSI-25_BASS-II/PSI-25_metadata_PSI_metadata_PSI-101_BASS-II.zip": "PSI-25 BASS-II Investigation Metadata (ISA-Tab i_Investigation.txt)",
    "PSI-107_SPICE/60054MAFH000-C SPICE Experiment Assembly.pdf": "SPICE Experiment Assembly Drawing (60054MAFH000-C)",
    "PSI-107_SPICE/Dotson_umd_0117N_10980.pdf": "Laminar Smoke Points of Coflow Diffusion Flames in Microgravity (K. Dotson M.S. Thesis, UMD 2010)",
    "PSI-107_SPICE/Exp_19-20_SPICE_30-Day_PostFlight_Report.pdf": "Increment 19/20 SPICE 30-Day Post-Flight Report",
    "PSI-107_SPICE/MEM-010.pdf": "SPICE Technical Memorandum MEM-010: Test Point Selection",
    "PSI-107_SPICE/SPICE Final Report 12_2_2012.pdf": "SPICE Final Science & Engineering Report (Dec 2, 2012)",
    "PSI-107_SPICE/SPICE Phase III Flight Safety Data Package_May 2008.pdf": "SPICE Phase III Flight Safety Data Package (May 2008)",
    "PSI-107_SPICE/SPICE RPT-002 Science Verif Report_May 2007.pdf": "SPICE Science Verification Report RPT-002 (May 2007)",
    "PSI-107_SPICE/SPICE SRD 8-23-07 with sigs.doc": "SPICE Science Requirements Document (Aug 23, 2007)",
    "PSI-107_SPICE/PSI-107_metadata_PSI-176_SPICE.zip": "PSI-107 SPICE Investigation Metadata (ISA-Tab i_Investigation.txt)",
}


def _slugify(name: str) -> str:
    stem = Path(name).stem
    s = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower()
    return s[:40]


def _clean_ws(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\u2028", "\n").replace("\u2029", "\n").replace("\x85", "\n")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _detect_heading(text: str) -> str | None:
    for line in text.split("\n")[:6]:
        s = line.strip()
        if not s or len(s) > 90:
            continue
        if re.match(r"^(\d+(\.\d+)*\s+[A-Z]|Section\s+\d|CHAPTER\s+\d|TABLE\s+\d| Appendix\s+[A-Z]|Background|Introduction|Objectives|Success Criteria)", s, re.I):
            return s
        if s.isupper() and 4 <= len(s) <= 70 and any(c.isalpha() for c in s):
            return s
    return None


def _chunk_text_segments(
    segments: list[tuple[int | None, str | None, str]],
    target_max: int = TARGET_MAX,
    overlap: int = OVERLAP,
) -> list[tuple[int | None, int | None, str | None, str]]:
    """Combine or split (page_num, section, text) segments into ~800-1,150 char chunks."""
    results: list[tuple[int | None, int | None, str | None, str]] = []
    cur_text = ""
    cur_p_start: int | None = None
    cur_p_end: int | None = None
    cur_sec: str | None = None

    def flush(txt: str, p_s: int | None, p_e: int | None, sec: str | None) -> None:
        cleaned = _clean_ws(txt)
        if cleaned:
            results.append((p_s, p_e, sec, cleaned))

    for page_num, sec, seg_text in segments:
        seg_text = _clean_ws(seg_text)
        if not seg_text:
            continue

        # Split oversized single page/segment by paragraphs or sentences
        paras = [p.strip() for p in seg_text.split("\n\n") if p.strip()]
        for para in paras:
            while len(para) > target_max:
                # Find a clean sentence/word break near target_max
                cut = para.rfind(". ", TARGET_MIN, target_max)
                if cut == -1:
                    cut = para.rfind(" ", TARGET_MIN, target_max)
                if cut == -1:
                    cut = target_max
                else:
                    cut += 1
                piece = para[:cut].strip()
                if cur_text and len(cur_text) + 2 + len(piece) > target_max:
                    flush(cur_text, cur_p_start, cur_p_end, cur_sec)
                    tail = cur_text[-overlap:].strip() if overlap > 0 else ""
                    cur_text = (tail + "\n\n" + piece).strip() if tail else piece
                    cur_p_start = page_num
                    cur_p_end = page_num
                    cur_sec = sec or cur_sec
                else:
                    if not cur_text:
                        cur_p_start = page_num
                        cur_sec = sec or cur_sec
                    cur_text = (cur_text + "\n\n" + piece).strip() if cur_text else piece
                    cur_p_end = page_num
                flush(cur_text, cur_p_start, cur_p_end, cur_sec)
                tail_piece = piece[-overlap:].strip() if overlap > 0 else ""
                para = (tail_piece + " " + para[cut:].strip()).strip()
                cur_text = ""
                cur_p_start = None
                cur_p_end = None

            if not para:
                continue

            if cur_text and len(cur_text) + 2 + len(para) > target_max:
                flush(cur_text, cur_p_start, cur_p_end, cur_sec)
                tail = cur_text[-overlap:].strip() if overlap > 0 else ""
                # Snap overlap tail to first space so we don't start mid-word
                sp = tail.find(" ")
                if 0 < sp < 30:
                    tail = tail[sp + 1 :]
                cur_text = (tail + "\n\n" + para).strip() if tail else para
                cur_p_start = cur_p_end if cur_p_end is not None else page_num
                cur_p_end = page_num
                cur_sec = sec or cur_sec
            else:
                if not cur_text:
                    cur_p_start = page_num
                    cur_sec = sec or cur_sec
                elif sec and not cur_sec:
                    cur_sec = sec
                cur_text = (cur_text + "\n\n" + para).strip() if cur_text else para
                cur_p_end = page_num

    if cur_text:
        flush(cur_text, cur_p_start, cur_p_end, cur_sec)

    return results


def _extract_pdf(path: Path) -> list[tuple[int | None, str | None, str]]:
    reader = pypdf.PdfReader(str(path))
    segments: list[tuple[int | None, str | None, str]] = []
    last_sec: str | None = None
    for idx, page in enumerate(reader.pages, start=1):
        txt = _clean_ws(page.extract_text() or "")
        if not txt:
            continue
        sec = _detect_heading(txt) or last_sec
        if sec:
            last_sec = sec
        segments.append((idx, sec, txt))
    return segments


def _extract_docx(path: Path) -> list[tuple[int | None, str | None, str]]:
    doc = docx.Document(str(path))
    segments: list[tuple[int | None, str | None, str]] = []
    cur_sec: str | None = None
    buf: list[str] = []
    for p in doc.paragraphs:
        t = _clean_ws(p.text)
        if not t:
            continue
        style_name = (p.style.name if p.style else "") or ""
        if "Heading" in style_name or "Title" in style_name or (len(t) < 80 and t.endswith("?")):
            if buf:
                segments.append((None, cur_sec, "\n\n".join(buf)))
                buf = []
            cur_sec = t
        buf.append(t)
    if buf:
        segments.append((None, cur_sec, "\n\n".join(buf)))

    # Also extract table contents if present
    for t_idx, table in enumerate(doc.tables, start=1):
        rows_txt = []
        for row in table.rows:
            cells = [_clean_ws(c.text) for c in row.cells]
            if any(cells):
                rows_txt.append(" | ".join(cells))
        if rows_txt:
            segments.append((None, cur_sec or f"Table {t_idx}", "\n".join(rows_txt)))
    return segments


def _extract_pptx(path: Path) -> list[tuple[int | None, str | None, str]]:
    pres = pptx.Presentation(str(path))
    segments: list[tuple[int | None, str | None, str]] = []
    for s_idx, slide in enumerate(pres.slides, start=1):
        parts: list[str] = []
        title: str | None = None
        if slide.shapes.title and slide.shapes.title.text:
            title = _clean_ws(slide.shapes.title.text)
        for sh in slide.shapes:
            if sh.has_text_frame:
                t = _clean_ws(sh.text_frame.text)
                if t:
                    parts.append(t)
        if parts:
            segments.append((s_idx, title or f"Slide {s_idx}", "\n\n".join(parts)))
    return segments


def _extract_legacy_doc(path: Path) -> list[tuple[int | None, str | None, str]]:
    b = path.read_bytes()
    start = b.find(b"Science Requirements for")
    if start == -1:
        return []
    end = b.find(b"\x00\x00", start)
    raw_slice = b[start:end].decode("cp1252", errors="ignore")
    clean = _clean_ws(raw_slice)
    if not clean:
        return []
    return [(None, "Science Requirements for SPICE", clean)]


def _extract_isa_zip(path: Path) -> list[tuple[int | None, str | None, str]]:
    segments: list[tuple[int | None, str | None, str]] = []
    with zipfile.ZipFile(path) as z:
        for name in z.namelist():
            if name.endswith("i_Investigation.txt"):
                raw = z.read(name).decode("utf-8", errors="replace")
                lines = []
                cur_sec = "ISA-Tab Investigation Overview"
                for line in raw.splitlines():
                    s = line.strip()
                    if not s or s.startswith("#"):
                        continue
                    parts = [p.strip('"').strip() for p in s.split("\t") if p.strip('"').strip()]
                    if not parts:
                        continue
                    if len(parts) == 1 and parts[0].isupper():
                        if lines:
                            segments.append((None, cur_sec, "\n".join(lines)))
                            lines = []
                        cur_sec = parts[0]
                    elif len(parts) >= 2:
                        key = parts[0]
                        vals = [v for v in parts[1:] if v]
                        if vals:
                            lines.append(f"{key}: {' | '.join(vals)}")
                if lines:
                    segments.append((None, cur_sec, "\n".join(lines)))
    return segments


def build_corpus() -> dict:
    raw_dir = ROOT / "data" / "raw"
    out_dir = ROOT / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load DOIs and licenses from source_registry.csv
    dois: dict[str, str] = {}
    licenses: dict[str, str] = {}
    with open(ROOT / "data" / "source_registry.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            dois[r["source_id"]] = r["doi"]
            licenses[r["source_id"]] = r["license"] or "CC0-1.0"

    # Load manifest entries
    manifest_rows = []
    with open(ROOT / "data" / "raw_manifest.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            manifest_rows.append(r)

    chunks: list[dict] = []
    skipped_docs: list[dict] = []
    docs_processed = 0

    for m in manifest_rows:
        rel_path = m["relative_path"]
        cat = m["category"]
        source_id = m["source_id"]
        sha256 = m["sha256"]

        # Include all documents, investigation_metadata zips, and the FLEX readme
        if cat not in ("document", "investigation_metadata") and not rel_path.endswith("Readme.txt"):
            continue

        full_path = raw_dir / rel_path
        ext = full_path.suffix.lower()

        if ext == ".pdf":
            segments = _extract_pdf(full_path)
        elif ext == ".docx":
            segments = _extract_docx(full_path)
        elif ext == ".pptx":
            segments = _extract_pptx(full_path)
        elif ext == ".doc":
            segments = _extract_legacy_doc(full_path)
        elif ext == ".zip":
            segments = _extract_isa_zip(full_path)
        elif ext == ".txt":
            segments = [(None, "Readme", _clean_ws(full_path.read_text(encoding="utf-8", errors="replace")))]
        else:
            continue

        chunk_tuples = _chunk_text_segments(segments)
        if not chunk_tuples:
            skipped_docs.append({
                "source_id": source_id,
                "doc_file": rel_path,
                "reason": "no_extractable_text (scanned drawing / image-only PDF)",
            })
            continue

        docs_processed += 1
        slug = _slugify(rel_path)
        doc_title = DOC_TITLES.get(rel_path, Path(rel_path).stem)

        for c_idx, (p_start, p_end, sec, text) in enumerate(chunk_tuples, start=1):
            p_tag = f"p{p_start}" if p_start is not None else "p0"
            chunk_id = f"{source_id}:{slug}:{p_tag}:c{c_idx:03d}"
            chunks.append({
                "chunk_id": chunk_id,
                "source_id": source_id,
                "doc_title": doc_title,
                "doc_file": rel_path,
                "doc_sha256": sha256,
                "page_start": p_start,
                "page_end": p_end,
                "section": sec,
                "text": text,
                "char_count": len(text),
                "license": licenses.get(source_id, "CC0-1.0"),
                "doi": dois.get(source_id, ""),
            })

    out_file = out_dir / "corpus_chunks.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    by_source: dict[str, int] = {}
    for ch in chunks:
        by_source[ch["source_id"]] = by_source.get(ch["source_id"], 0) + 1

    return {
        "total_chunks": len(chunks),
        "docs_processed": docs_processed,
        "skipped_docs": skipped_docs,
        "chunks_by_source": by_source,
    }


if __name__ == "__main__":
    summary = build_corpus()
    print(json.dumps(summary, indent=2))
