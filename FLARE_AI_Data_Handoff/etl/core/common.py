"""Shared ETL core: raw verification, value parsing, row building, validation, duplicates.

Every rule here comes from etl/contract/DATA_CONTRACT.md. If you change behaviour, update the contract.
"""
from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
MANIFEST = ROOT / "data" / "raw_manifest.csv"
REGISTRY = ROOT / "data" / "source_registry.csv"

ETL_VERSION = "0.1.0"
CONTRACT_VERSION = "v0.3"
MMHG_TO_KPA = 0.133322

MISSING_REASONS = {"unavailable_in_source", "not_reported", "invalid_value", "not_parseable", "pending_review"}
GRAVITY = {"microgravity", "partial_gravity", "normal_gravity", "unknown"}
DOMAINS = {"liquid_droplet", "solid", "gas_jet", "smoke"}
PLATFORMS = {"ISS", "Cygnus", "ground", "drop_tower", "aircraft", "unknown"}

RUN_FIELDS = [
    "run_id", "source_id", "investigation", "native_test_id", "domain", "platform",
    "gravity_regime", "gravity_evidence_id", "test_date", "test_date_raw", "test_time_gmt",
    "fuel_raw", "fuel", "fuel_detail",
    "o2_vol_pct", "o2_basis", "o2_missing_reason", "o2_raw", "o2_raw_unit",
    "pressure_kpa", "pressure_missing_reason", "pressure_raw", "pressure_raw_unit",
    "flow_cm_s", "flow_basis", "flow_missing_reason", "flow_raw", "flow_raw_unit",
    "outcome_raw", "dup_status", "dup_of", "qa_flags",
    "source_file", "source_sha256", "source_row", "etl_version",
]
MEAS_FIELDS = ["run_id", "variable", "value_num", "value_text", "unit", "missing_reason", "source_column"]

# Cell contents that mean "nothing was recorded".
BLANK_TOKENS = {"", "-", "\u2013", "\u2014", "none", "n/a", "na"}
# Cell contents that mean "the sensor was out of range / invalid".
INVALID_TOKENS = {"or", "over", "los", "ku los", "no ku"}
NUM_RE = re.compile(r"^-?(\d+\.?\d*|\.\d+)$")


# ---------------------------------------------------------------- raw access
def load_manifest() -> dict[str, dict]:
    with open(MANIFEST, encoding="utf-8-sig", newline="") as f:
        return {r["relative_path"]: r for r in csv.DictReader(f)}


def verify_raw() -> list[str]:
    """Same checks as etl/core/verify_raw.ps1. Returns a list of problems (empty = OK)."""
    problems = []
    manifest = load_manifest()
    for rel, m in manifest.items():
        p = RAW / rel
        if not p.exists():
            problems.append(f"MISSING  {rel}")
            continue
        if hashlib.sha256(p.read_bytes()).hexdigest() != m["sha256"]:
            problems.append(f"CHANGED  {rel}")
    listed = {(RAW / r).resolve() for r in manifest}
    for p in RAW.rglob("*"):
        if p.is_file() and p.resolve() not in listed:
            problems.append(f"UNLISTED {p.relative_to(RAW)}")
    return problems


def read_raw_table(rel_path: str, encoding: str) -> tuple[list[dict], list[str], str]:
    """Read a raw CSV as text only (no type guessing). Returns rows, headers, sha256."""
    data = (RAW / rel_path).read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    manifest = load_manifest()
    if rel_path not in manifest or manifest[rel_path]["sha256"] != sha:
        raise RuntimeError(f"{rel_path}: SHA-256 does not match manifest - refusing to parse")
    reader = csv.DictReader(io.StringIO(data.decode(encoding)))
    return list(reader), reader.fieldnames, sha


# ---------------------------------------------------------------- parsing
def clean_text(v: str | None) -> str:
    return re.sub(r"\s+", " ", v or "").strip()


def parse_num(v: str | None) -> tuple[float | None, str | None]:
    """Strict number parse. Returns (value, missing_reason). Never guesses."""
    t = clean_text(v)
    low = t.lower()
    if low in BLANK_TOKENS:
        return None, "not_reported"
    if low in INVALID_TOKENS:
        return None, "invalid_value"
    if NUM_RE.match(t):
        return float(t), None
    return None, "not_parseable"  # e.g. '~6', '>500', '3.5 (68) 1.7'


def parse_mdy(v: str) -> str | None:
    m = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", clean_text(v))
    if not m:
        return None
    mo, d, y = map(int, m.groups())
    return f"{y:04d}-{mo:02d}-{d:02d}"


def parse_time(v: str) -> tuple[str | None, bool]:
    """Normalise a GMT time. Returns (time, unparsed_flag).
    Accepts HH:MM:SS, HH.MM.SS, HHMM. Seconds are never invented: HHMM -> 'HH:MM'."""
    t = clean_text(v)
    if t.lower() in BLANK_TOKENS | INVALID_TOKENS:
        return None, False
    m = re.fullmatch(r"(\d{1,2})[:.](\d{2})[:.](\d{2})", t)
    if m:
        h, mi, s = map(int, m.groups())
        if h < 24 and mi < 60 and s < 60:
            return f"{h:02d}:{mi:02d}:{s:02d}", False
    m = re.fullmatch(r"(\d{2})(\d{2})", t)
    if m:
        h, mi = map(int, m.groups())
        if h < 24 and mi < 60:
            return f"{h:02d}:{mi:02d}", False
    return None, True


def fmt(x):
    """Format numbers without float noise (e.g. 101.0151 not 101.01510000000002)."""
    if x is None:
        return ""
    if isinstance(x, float):
        return f"{round(x, 6):g}" if abs(x) < 1e15 else repr(x)
    return x


# ---------------------------------------------------------------- run objects
@dataclass
class Run:
    data: dict
    measurements: list[dict] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)
    raw_cells: tuple = ()          # all raw cells, for exact-duplicate detection
    near_key: tuple | None = None  # identity key for near-duplicate detection
    near_nums: tuple = ()          # numeric values compared within tolerance

    def flag(self, f: str):
        if f not in self.flags:
            self.flags.append(f)

    def measure(self, row: dict, column: str, variable: str, unit: str | None, numeric=True):
        raw = row.get(column, "")
        text = clean_text(raw)
        if numeric:
            val, reason = parse_num(raw)
            if unit is None and val is not None:
                val, reason = None, "unavailable_in_source"  # number with undefined unit: never guess
        else:
            val, reason = None, (None if text else "not_reported")
        self.measurements.append({
            "run_id": self.data["run_id"], "variable": variable, "value_num": fmt(val),
            "value_text": text, "unit": unit or "", "missing_reason": reason or "",
            "source_column": column,
        })


def new_run(source_id: str, investigation: str, native_key: str, source_file: str,
            sha: str, source_row: int, **fields) -> dict:
    d = {k: "" for k in RUN_FIELDS}
    d.update(run_id=f"{source_id}:{native_key}", source_id=source_id, investigation=investigation,
             source_file=source_file, source_sha256=sha, source_row=source_row,
             etl_version=ETL_VERSION, dup_status="unique")
    d.update(fields)
    return d


# ---------------------------------------------------------------- validation
def validate(runs: list[Run]) -> tuple[list[Run], list[dict]]:
    """Apply hard rules (reject) and soft rules (flag). Returns kept runs and rejected records."""
    manifest_sha = {m["sha256"] for m in load_manifest().values()}
    kept, rejected, seen = [], [], set()
    for r in runs:
        d, reasons = r.data, []
        # Physically impossible canonical values: blank the value (raw kept in *_raw), keep the run, flag it.
        for col, reason_col, bad in (("o2_vol_pct", "o2_missing_reason", lambda v: not 0 <= v <= 100),
                                     ("pressure_kpa", "pressure_missing_reason", lambda v: v <= 0)):
            if d[col] != "" and bad(float(d[col])):
                d[col], d[reason_col] = "", "invalid_value"
                if col == "o2_vol_pct":
                    d["o2_basis"] = ""
                r.flag("impossible_value_nulled")
        if not d["run_id"] or d["run_id"] in seen:
            reasons.append("run_id_missing_or_duplicate")
        if d["gravity_regime"] not in GRAVITY:
            reasons.append("invalid_gravity_regime")
        if d["gravity_regime"] == "partial_gravity" and not d["gravity_evidence_id"]:
            reasons.append("partial_gravity_without_evidence")
        if d["domain"] not in DOMAINS or d["platform"] not in PLATFORMS:
            reasons.append("invalid_domain_or_platform")
        if d["source_sha256"] not in manifest_sha:
            reasons.append("sha256_not_in_manifest")
        o2, p, fl = d["o2_vol_pct"], d["pressure_kpa"], d["flow_cm_s"]
        if o2 != "" and not (0 <= float(o2) <= 100):
            reasons.append("o2_out_of_0_100")
        if p != "" and float(p) <= 0:
            reasons.append("pressure_not_positive")
        for val, reason, name in ((o2, d["o2_missing_reason"], "o2"), (p, d["pressure_missing_reason"], "pressure"),
                                  (fl, d["flow_missing_reason"], "flow")):
            if val == "" and reason not in MISSING_REASONS:
                reasons.append(f"{name}_null_without_valid_reason")
        if reasons:
            rejected.append({"run_id": d["run_id"], "source_id": d["source_id"], "source_row": d["source_row"],
                             "reasons": ";".join(reasons)})
            continue
        seen.add(d["run_id"])
        # soft rules
        if fl != "" and float(fl) < 0:
            r.flag("below_physical_range")
        if o2 != "" and not (10 <= float(o2) <= 50):
            r.flag("o2_unusual")
        if p != "" and not (20 <= float(p) <= 400):
            r.flag("pressure_unusual")
        if d["fuel"].casefold() != d["fuel_raw"].casefold():  # case-only changes are not worth a flag
            r.flag("fuel_label_normalised")
        kept.append(r)
    return kept, rejected


def mark_duplicates(runs: list[Run], tolerance: float = 0.02):
    """Exact duplicate: all raw cells identical to an earlier row in the same source.
    Near duplicate: same near_key and every numeric within `tolerance` (relative) of an earlier row."""
    first_exact: dict[tuple, str] = {}
    by_key: dict[tuple, list[Run]] = {}
    for r in runs:
        d = r.data
        ek = (d["source_id"],) + r.raw_cells
        if ek in first_exact:
            d["dup_status"], d["dup_of"] = "exact_duplicate", first_exact[ek]
            continue
        first_exact[ek] = d["run_id"]
        if r.near_key is None:
            continue
        nk = (d["source_id"],) + r.near_key
        for earlier in by_key.get(nk, []):
            if _close(r.near_nums, earlier.near_nums, tolerance):
                d["dup_status"], d["dup_of"] = "near_duplicate", earlier.data["run_id"]
                break
        by_key.setdefault(nk, []).append(r)


def _close(a: tuple, b: tuple, tol: float) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x is None and y is None:
            continue
        if x is None or y is None:
            return False
        if abs(x - y) > tol * max(abs(x), abs(y), 1e-9):
            return False
    return True
