"""
FLARE AI - explainable similarity ranking (Analytics & Ranking workstream).

Given the conditions a researcher selects (oxygen %, pressure, airflow, plus the
combustion domain), rank past experiments by how close their conditions are.

What this score IS:   a research-relevance score ("similar test conditions").
What this score IS NOT: a probability of ignition, a fire-risk score, or a
prediction of fire behaviour on the Moon or Mars.

Pipeline (all steps are plain pandas/numpy, no database or LLM needed):
  1. validate the query
  2. filter to compatible experiments (same domain, optional gravity level)
  3. drop selected variables that NO experiment in that domain reports (and say so)
     normalise each remaining variable to a 0-1 scale
  4. per experiment, take the weighted distance over the variables it HAS
     (missing values stay missing - they are never filled in)
  5. similarity = 1 - distance; score = similarity x coverage (share of the selected
     variables the experiment reports); rank, and attach an explanation

Column names below are placeholders: agree the real ones with data engineering
and change them here, in one place.
"""
from __future__ import annotations

import math
import numbers
from typing import Any, Optional

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Configuration - the "contract" with the data pipeline
# --------------------------------------------------------------------------
ID_COL = "experiment_id"
DOMAIN_COL = "domain"            # "solid" | "gas_jet" | "liquid_droplet" | "smoke"
GRAVITY_COL = "gravity_level"    # "microgravity" | "normal_gravity"
SOURCE_COL = "source_url"        # link back to NASA PSI (optional column)

# optional columns copied into each result so the UI can show them
CONTEXT_COLS = ["investigation", "source_id", "native_test_id", "fuel", "platform",
                "gravity_level", "dup_status", "qa_flags"]
# variable column -> column holding the reason it is missing (optional)
MISSING_REASON_COLS = {
    "o2_percent": "o2_missing_reason",
    "pressure_psi": "pressure_missing_reason",
    "airflow_cm_s": "flow_missing_reason",
}

# variable column -> human-readable label
FEATURE_COLS = {
    "o2_percent": "Oxygen (%)",
    "pressure_psi": "Pressure (psi)",
    "airflow_cm_s": "Airflow velocity (cm/s)",
}
DEFAULT_WEIGHTS = {name: 1.0 for name in FEATURE_COLS}

# Domains a user can search in - these are the names in Data Contract v0.3.
# Rows with any other label never match a query (the domain gate).
VALID_DOMAINS = ("solid", "gas_jet", "liquid_droplet", "smoke")
# Deliberately no "partial gravity" option: we do not claim PSI has that data.
VALID_GRAVITY = ("microgravity", "normal_gravity")

# True: score = similarity x coverage, so an experiment that can only be compared on
# half of the selected variables cannot outrank a fully compared, similar one.
# False: score = similarity only (partial matches can tie for first place).
COVERAGE_WEIGHTED_SCORE = True

DISCLAIMER = (
    "Ranks research relevance only (similarity of test conditions). "
    "Not a fire-risk score, not an ignition probability, and not a prediction "
    "of fire behaviour in lunar or Martian gravity. Decision-support prototype."
)


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _is_number(x: Any) -> bool:
    return (
        isinstance(x, numbers.Real)
        and not isinstance(x, bool)
        and math.isfinite(float(x))
    )


def _validate_query(query: dict, weights: Optional[dict]):
    """Check the user's input. Returns (domain, gravity, conditions, weights)."""
    if not isinstance(query, dict):
        raise ValueError("query must be a dict")

    domain = query.get("domain")
    if domain not in VALID_DOMAINS:
        raise ValueError(f"domain must be one of {VALID_DOMAINS}, got {domain!r}")

    gravity = query.get("gravity")
    if gravity is not None and gravity not in VALID_GRAVITY:
        raise ValueError(
            f"gravity must be one of {VALID_GRAVITY} or omitted, got {gravity!r} "
            "(there is intentionally no 'partial gravity' category)"
        )

    conditions = {}
    for name in FEATURE_COLS:
        value = query.get(name)
        if value is None:
            continue
        if not _is_number(value):
            raise ValueError(f"{name} must be a finite number, got {value!r}")
        conditions[name] = float(value)
    if not conditions:
        raise ValueError(f"give at least one condition from {list(FEATURE_COLS)}")

    w = dict(DEFAULT_WEIGHTS)
    for name, value in (weights or {}).items():
        if name not in FEATURE_COLS:
            raise ValueError(f"unknown weight {name!r}; expected {list(FEATURE_COLS)}")
        if not _is_number(value) or value < 0:
            raise ValueError(f"weight for {name} must be a number >= 0, got {value!r}")
        w[name] = float(value)
    w = {name: w[name] for name in conditions}  # only variables the user chose
    total = sum(w.values())
    if total <= 0:
        raise ValueError("at least one selected variable needs a weight > 0")
    w = {name: value / total for name, value in w.items()}  # sum to 1
    return domain, gravity, conditions, w


def _closeness_label(normalized_diff: float) -> str:
    # Relative to the spread of the candidate experiments, not absolute units.
    if normalized_diff <= 0.10:
        return "very close"
    if normalized_diff <= 0.25:
        return "close"
    if normalized_diff <= 0.50:
        return "moderate"
    return "far"


def _fmt(x: float) -> str:
    return f"{x:g}"


def _clean(value):
    """Table cell -> JSON-safe text, or None when missing."""
    return None if pd.isna(value) else str(value)


def _empty_response(query_info, n_excluded, n_candidates=0, n_dropped=0, notes=None):
    return {
        "query": query_info,
        "results": [],
        "notes": notes or [],
        "n_candidates": n_candidates,
        "n_excluded_by_domain_or_gravity": n_excluded,
        "n_dropped_insufficient_data": n_dropped,
        "disclaimer": DISCLAIMER,
    }


# --------------------------------------------------------------------------
# Main entry point
# --------------------------------------------------------------------------
def rank_experiments(
    experiments: pd.DataFrame,
    query: dict,
    weights: Optional[dict] = None,
    top_k: Optional[int] = 10,
    min_coverage: float = 0.5,
) -> dict:
    """
    Rank experiments by closeness to the selected conditions.

    experiments   table with ID_COL, DOMAIN_COL, the variable columns, and
                  optionally GRAVITY_COL / SOURCE_COL. Missing values = NaN/None.
    query         e.g. {"domain": "gas", "o2_percent": 21, "pressure_psi": 14.7,
                        "airflow_cm_s": 10, "gravity": "microgravity"}
                  (only "domain" and at least one variable are required)
    weights       optional {variable: weight}; relative importance, defaults to equal
    top_k         how many results to return (None = all)
    min_coverage  fraction of the selected weight an experiment must have data
                  for; below this it is dropped instead of ranked on thin data

    Returns a JSON-friendly dict: {"query", "results": [...], counts, "disclaimer"}.
    """
    if not 0.0 <= min_coverage <= 1.0:
        raise ValueError("min_coverage must be between 0 and 1")

    domain, gravity, q, w = _validate_query(query, weights)
    features = list(q)

    needed = [ID_COL, DOMAIN_COL, *features] + ([GRAVITY_COL] if gravity else [])
    absent = [c for c in needed if c not in experiments.columns]
    if absent:
        raise ValueError(f"experiments table is missing required column(s): {absent}")

    query_info = {
        "domain": domain,
        "gravity": gravity,
        "conditions": q,
        "weights": {name: round(value, 4) for name, value in w.items()},
    }

    # Step 2: only compare compatible experiments (excluded, not just ranked low)
    pool = experiments[experiments[DOMAIN_COL] == domain]
    if gravity is not None:
        pool = pool[pool[GRAVITY_COL] == gravity]
    n_excluded = len(experiments) - len(pool)
    pool = pool.reset_index(drop=True)
    if pool.empty:
        return _empty_response(query_info, n_excluded)

    # Step 3: normalise. Values that cannot be read as numbers become NaN
    # (= missing). The scale for each variable runs from the smallest to the
    # largest value among the candidates AND the user's chosen value, so every
    # normalised difference lands between 0 and 1.
    X = pool[features].apply(pd.to_numeric, errors="coerce").astype(float)

    # Variables that NO experiment in this domain reports cannot be compared, so
    # they are left out (and we say so) instead of making every experiment look
    # like it has "missing data". Weights are re-scaled over what is left.
    notes = []
    not_measured = [f for f in features if not X[f].notna().any()]
    for f in not_measured:
        notes.append(
            f"{FEATURE_COLS[f]} is not reported by any '{domain}' experiment in the "
            "current data, so it was left out of the ranking."
        )
    features = [f for f in features if f not in not_measured]
    query_info["not_measured_in_domain"] = not_measured
    query_info["variables_used"] = features
    weight_total = sum(w[f] for f in features)
    if not features or weight_total <= 0:
        notes.append(
            "None of the selected variables with a weight above 0 are reported for this "
            "domain, so nothing could be ranked."
        )
        return _empty_response(query_info, n_excluded, len(pool), 0, notes)
    q = {f: q[f] for f in features}
    w = {f: w[f] / weight_total for f in features}
    query_info["weights"] = {name: round(value, 4) for name, value in w.items()}
    X = X[features]
    q_ser = pd.Series(q, index=features)
    w_ser = pd.Series(w, index=features)

    span = {}
    for f in features:
        values = np.append(X[f].to_numpy(dtype=float), q[f])
        span[f] = float(np.nanmax(values) - np.nanmin(values))
    span = pd.Series(span, index=features).replace(0.0, 1.0)  # avoid divide-by-zero

    diffs = X.sub(q_ser, axis=1).abs().div(span, axis=1)  # NaN where data missing

    # Step 4: weighted distance over the variables each experiment actually has.
    # Weights are re-scaled over those variables so experiments with different
    # gaps stay comparable. A missing value is skipped, never filled in.
    available = diffs.notna()
    w_avail = available.astype(float).mul(w_ser, axis=1)
    avail_w = w_avail.sum(axis=1)
    coverage = avail_w / float(w_ser.sum())
    weighted_sq = (diffs.pow(2).fillna(0.0) * w_avail).sum(axis=1)
    distance = np.sqrt(weighted_sq / avail_w.where(avail_w > 0))
    similarity = 1.0 - distance  # 1.0 = identical conditions, 0.0 = as far as possible
    score = similarity * coverage if COVERAGE_WEIGHTED_SCORE else similarity

    usable = distance.notna() & (coverage >= min_coverage - 1e-9)
    n_dropped = int((~usable).sum())

    # Step 5: rank (ties: more data first, then ID, so results are repeatable)
    table = pd.DataFrame(
        {
            "score": score.round(9),
            "coverage": coverage,
            "_id": pool[ID_COL].astype(str),
        }
    )[usable]
    table = table.sort_values(
        ["score", "coverage", "_id"], ascending=[False, False, True], kind="mergesort"
    )
    if top_k is not None:
        table = table.head(top_k)

    results = []
    for rank, idx in enumerate(table.index, start=1):
        avail_sum = float(avail_w[idx])
        breakdown, parts, missing_labels = [], [], []
        for f in features:
            label = FEATURE_COLS[f]
            if available.at[idx, f]:
                d = float(diffs.at[idx, f])
                closeness = _closeness_label(d)
                parts.append(
                    f"{label}: {closeness} "
                    f"(experiment {_fmt(X.at[idx, f])} vs selected {_fmt(q[f])})"
                )
                breakdown.append(
                    {
                        "variable": f,
                        "label": label,
                        "selected_value": q[f],
                        "experiment_value": float(X.at[idx, f]),
                        "normalized_difference": round(d, 4),
                        "weight_used": round(float(w_ser[f]) / avail_sum, 4),
                        "closeness": closeness,
                        "missing_reason": None,
                    }
                )
            else:
                missing_labels.append(label)
                reason_col = MISSING_REASON_COLS.get(f)
                reason = _clean(pool.at[idx, reason_col]) if reason_col in pool.columns else None
                breakdown.append(
                    {
                        "variable": f,
                        "label": label,
                        "selected_value": q[f],
                        "experiment_value": None,
                        "normalized_difference": None,
                        "weight_used": 0.0,
                        "closeness": "not reported",
                        "missing_reason": reason,
                    }
                )

        n_used = len(features) - len(missing_labels)
        sim_here = float(similarity[idx])
        if COVERAGE_WEIGHTED_SCORE and coverage[idx] < 1.0 - 1e-9:
            head = (
                f"Relevance score {table.at[idx, 'score']:.2f} = similarity {sim_here:.2f} on the "
                f"compared variables x coverage {coverage[idx]:.2f}. "
            )
        else:
            head = f"Relevance score {table.at[idx, 'score']:.2f}. "
        explanation = (
            head
            + f"Compared on {n_used} of {len(features)} selected variables. "
            + "; ".join(parts)
            + "."
        )
        if missing_labels:
            explanation += (
                f" Not reported: {', '.join(missing_labels)} "
                "(left out of the score, not assumed)."
            )

        src = pool.at[idx, SOURCE_COL] if SOURCE_COL in pool.columns else None
        results.append(
            {
                "rank": rank,
                "experiment_id": str(pool.at[idx, ID_COL]),
                "score": round(float(table.at[idx, "score"]), 4),
                "similarity": round(sim_here, 4),
                "distance": round(float(distance[idx]), 4),
                "coverage": round(float(coverage[idx]), 3),
                "matched_variables": [b["variable"] for b in breakdown if b["experiment_value"] is not None],
                "missing_variables": [b["variable"] for b in breakdown if b["experiment_value"] is None],
                "breakdown": breakdown,
                "explanation": explanation,
                "source_link": None if pd.isna(src) else str(src),
                "context": {c: _clean(pool.at[idx, c]) for c in CONTEXT_COLS if c in pool.columns},
            }
        )

    if n_excluded:
        notes.append(
            f"{n_excluded} experiments were not compared because they belong to a different "
            "combustion domain or gravity regime."
        )
    if n_dropped:
        notes.append(
            f"{n_dropped} experiments in this domain were left out because they report too "
            f"few of the selected variables (coverage below {min_coverage:.0%})."
        )

    return {
        "query": query_info,
        "results": results,
        "notes": notes,
        "n_candidates": len(pool),
        "n_excluded_by_domain_or_gravity": n_excluded,
        "n_dropped_insufficient_data": n_dropped,
        "disclaimer": DISCLAIMER,
    }