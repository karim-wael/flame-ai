"""
adapter.py - turns Farah El Qady's Data Contract v0.3 `processed/runs.csv` into
the table that rank_experiments() expects.

Contract column  ->  ranking column
  run_id              experiment_id
  domain              domain            (solid | gas_jet | liquid_droplet | smoke)
  gravity_regime      gravity_level
  o2_vol_pct          o2_percent        (already % by volume, 0-100)
  pressure_kpa        pressure_psi      (kPa x 0.145037738)
  flow_cm_s           airflow_cm_s      (already cm/s)
  *_missing_reason    kept as is, so results can say WHY a value is missing
  investigation, fuel, platform, qa_flags, dup_status, ... passed through

Rules (same spirit as the contract):
  * NEVER guess. A value outside its physical range becomes missing (reason
    'invalid_value') and is written to the issues report.
  * Missing stays missing; a real 0 (still air) stays 0.
  * By default only independent measurements are ranked: exact/near duplicates
    and secondary-aging re-measurements are hidden (contract section 10). Use
    include_duplicates / include_secondary_aging to bring them back.
  * Rows whose gravity regime is 'unknown' (e.g. the 8 SAME summary rows, I-028) are
    hidden from ranking by default so they never sit next to confirmed microgravity
    runs. They stay in the data/explorer. Use include_unknown_gravity=True to rank them.
  * Negative airflow (SPICE calibration artefact, issue I-016) is a science
    decision: negative_flow = "missing" (default), "clamp" (set to 0) or "keep".
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ranking import VALID_DOMAINS

KPA_TO_PSI = 0.145037738
REQUIRED = ["run_id", "domain", "gravity_regime", "o2_vol_pct", "pressure_kpa", "flow_cm_s"]
PASSTHROUGH = [
    "investigation", "source_id", "native_test_id", "fuel", "platform",
    "dup_status", "qa_flags",
    "o2_missing_reason", "pressure_missing_reason", "flow_missing_reason",
]


def build_ranking_table(
    runs: pd.DataFrame,
    registry: pd.DataFrame | None = None,
    include_duplicates: bool = False,
    include_secondary_aging: bool = False,
    include_unknown_gravity: bool = False,
    negative_flow: str = "missing",
):
    """
    runs      contents of processed/runs.csv (any subset of rows)
    registry  optional contents of data/source_registry.csv; its `doi` column is
              used to build a source link (https://doi.org/<doi>) per run

    Returns (table, issues). table.attrs["hidden"] says how many rows were hidden.
    """
    if negative_flow not in ("missing", "clamp", "keep"):
        raise ValueError("negative_flow must be 'missing', 'clamp' or 'keep'")
    absent = [c for c in REQUIRED if c not in runs.columns]
    if absent:
        raise ValueError(f"runs table is missing required column(s): {absent}")

    runs = runs.reset_index(drop=True)
    n = len(runs)
    ids = runs["run_id"].astype(str)
    issues: list[dict] = []

    def flag(i, field, problem):
        issues.append({"experiment_id": ids[i], "field": field, "problem": problem})

    # ---- which rows are ranked --------------------------------------------
    flags = runs["qa_flags"].fillna("").astype(str) if "qa_flags" in runs else pd.Series("", index=runs.index)
    dup = runs["dup_status"].fillna("unique") if "dup_status" in runs else pd.Series("unique", index=runs.index)
    is_dup = dup != "unique"
    is_aging = flags.str.contains("secondary_aging_remeasurement", regex=False)
    is_unknown = runs["gravity_regime"].fillna("unknown") == "unknown"
    keep = pd.Series(True, index=runs.index)
    if not include_duplicates:
        keep &= ~is_dup
    if not include_secondary_aging:
        keep &= ~is_aging
    if not include_unknown_gravity:
        keep &= ~is_unknown
    hidden = {
        "duplicates": 0 if include_duplicates else int(is_dup.sum()),
        "secondary_aging": 0 if include_secondary_aging else int((is_aging & ~is_dup).sum()),
        "unknown_gravity": 0 if include_unknown_gravity else int((is_unknown & ~is_dup & ~is_aging).sum()),
    }

    # ---- numbers -----------------------------------------------------------
    o2_raw, p_raw, f_raw = (pd.to_numeric(runs[c], errors="coerce") for c in ("o2_vol_pct", "pressure_kpa", "flow_cm_s"))
    o2, psi, flow = (np.full(n, np.nan) for _ in range(3))
    def reason_col(name):
        if name in runs.columns:
            return runs[name].copy().astype(object)
        return pd.Series(None, index=runs.index, dtype=object)

    reasons = {k: reason_col(k) for k in ("o2_missing_reason", "pressure_missing_reason", "flow_missing_reason")}

    def check_not_number(i, col, series, reason_key):
        if np.isnan(series[i]) and not pd.isna(runs.at[i, col]):
            flag(i, col, f"not a number: {runs.at[i, col]!r}")
            reasons[reason_key].at[i] = "invalid_value"

    for i in range(n):
        if not keep[i]:
            continue
        # oxygen: % by volume, must be 0-100
        check_not_number(i, "o2_vol_pct", o2_raw, "o2_missing_reason")
        if not np.isnan(o2_raw[i]):
            if 0.0 <= o2_raw[i] <= 100.0:
                o2[i] = o2_raw[i]
            else:
                flag(i, "o2_vol_pct", f"impossible oxygen value {o2_raw[i]:g}")
                reasons["o2_missing_reason"].at[i] = "invalid_value"
        # pressure: kPa -> psi, must be > 0
        check_not_number(i, "pressure_kpa", p_raw, "pressure_missing_reason")
        if not np.isnan(p_raw[i]):
            if p_raw[i] > 0:
                psi[i] = p_raw[i] * KPA_TO_PSI
            else:
                flag(i, "pressure_kpa", f"pressure must be > 0, got {p_raw[i]:g}")
                reasons["pressure_missing_reason"].at[i] = "invalid_value"
        # flow: cm/s; 0 is a real value, negative is a calibration artefact
        check_not_number(i, "flow_cm_s", f_raw, "flow_missing_reason")
        if not np.isnan(f_raw[i]):
            if f_raw[i] >= 0:
                flow[i] = f_raw[i]
            elif negative_flow == "keep":
                flow[i] = f_raw[i]
                flag(i, "flow_cm_s", f"negative flow {f_raw[i]:g} kept as is (I-016)")
            elif negative_flow == "clamp":
                flow[i] = 0.0
                flag(i, "flow_cm_s", f"negative flow {f_raw[i]:g} clamped to 0 (I-016)")
            else:
                flag(i, "flow_cm_s", f"negative flow {f_raw[i]:g} treated as missing (I-016)")
                reasons["flow_missing_reason"].at[i] = "invalid_value"

    # ---- labels ------------------------------------------------------------
    for i in np.flatnonzero(keep.to_numpy() & ~runs["domain"].isin(VALID_DOMAINS).to_numpy()):
        flag(i, "domain", f"domain {runs.at[i, 'domain']!r} is not searchable (excluded by the domain gate)")
    for i in np.flatnonzero(keep.to_numpy() & ids.duplicated(keep=False).to_numpy()):
        flag(i, "run_id", "duplicate run_id")

    table = pd.DataFrame(
        {
            "experiment_id": ids,
            "domain": runs["domain"],
            "gravity_level": runs["gravity_regime"],
            "o2_percent": o2,
            "pressure_psi": psi,
            "airflow_cm_s": flow,
        }
    )
    for col in PASSTHROUGH:
        if col in runs.columns:
            table[col] = reasons[col] if col in reasons else runs[col]

    link = None
    if registry is not None and {"source_id", "doi"} <= set(registry.columns) and "source_id" in runs.columns:
        link = runs["source_id"].map(dict(zip(registry["source_id"], "https://doi.org/" + registry["doi"].astype(str))))
    table["source_url"] = link if link is not None else None

    table = table[keep].reset_index(drop=True)
    table.attrs["hidden"] = hidden
    issues_df = pd.DataFrame(issues, columns=["experiment_id", "field", "problem"])
    return table, issues_df