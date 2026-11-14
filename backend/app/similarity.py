import sys
from functools import lru_cache
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session, selectinload

from .config import HANDOFF_DIR, RANKING_DIR, SCIENTIFIC_DISCLAIMER
from .models import ExperimentRun, Investigation
from .schemas import CompareRequest

# Add flare_ranking directory to Python path so adapter.py and ranking.py can be imported cleanly
if str(RANKING_DIR) not in sys.path:
    sys.path.insert(0, str(RANKING_DIR))

from adapter import build_ranking_table  # type: ignore  # noqa: E402
from ranking import FEATURE_COLS, rank_experiments  # type: ignore  # noqa: E402

KPA_TO_PSI = 0.145037738

# Map API canonical domain names <-> Data Contract v0.3 domain names used by flare_ranking
API_TO_RANKING_DOMAIN = {
    "solid": "solid",
    "gas": "gas_jet",
    "gas_jet": "gas_jet",
    "liquid_droplet": "liquid_droplet",
    "aerosol_smoke": "smoke",
    "smoke": "smoke",
}
RANKING_TO_API_DOMAIN = {
    "solid": "solid",
    "gas_jet": "gas",
    "liquid_droplet": "liquid_droplet",
    "smoke": "aerosol_smoke",
}


@lru_cache(maxsize=1)
def get_ranking_table():
    runs = pd.read_csv(HANDOFF_DIR / "processed" / "runs.csv", low_memory=False)
    registry = pd.read_csv(HANDOFF_DIR / "data" / "source_registry.csv")
    table, issues = build_ranking_table(runs, registry)
    return table, issues


def _format_ranking_item(
    r: Dict[str, Any],
    db_runs_by_code: Dict[str, ExperimentRun],
    is_baseline: bool = False,
) -> Dict[str, Any]:
    run_code = r["experiment_id"]
    db_run = db_runs_by_code.get(run_code)
    inv = db_run.investigation if db_run else None
    ctx = r.get("context", {})
    breakdown = r.get("breakdown", [])

    # Build feature_breakdown & missing_features in the shape expected by the frontend
    feature_breakdown: Dict[str, Any] = {}
    missing_features: List[Dict[str, str]] = []
    for b in breakdown:
        var = b["variable"]
        if b["experiment_value"] is not None:
            feature_breakdown[var] = {
                "status": "measured",
                "target": b["selected_value"],
                "record_value": b["experiment_value"],
                "normalized_delta": b["normalized_difference"],
                "closeness": b["closeness"],
            }
        else:
            reason = b.get("missing_reason") or "not_reported"
            missing_features.append({"feature": var, "missing_reason": reason})
            feature_breakdown[var] = {
                "status": "missing",
                "missing_reason": reason,
            }

    outcomes = []
    if db_run:
        outcomes = [
            {
                "id": m.id,
                "variable_name": m.variable_name,
                "canonical_field": m.canonical_field,
                "value_numeric": m.value_numeric,
                "value_text": m.value_text,
                "unit": m.unit,
                "normalized_value": m.normalized_value,
                "normalized_unit": m.normalized_unit,
                "value_status": m.value_status,
                "uncertainty": m.uncertainty,
                "missing_reason": m.missing_reason,
            }
            for m in db_run.measurements
        ]

    sf_name = None
    sf_sha = None
    if db_run and db_run.run_metadata:
        sf_name = db_run.run_metadata.get("source_file")
    if inv and inv.source_files:
        sf_sha = inv.source_files[0].checksum_sha256

    item = {
        "rank": r.get("rank"),
        "run_id": db_run.id if db_run else run_code,
        "run_code": run_code,
        "investigation_id": inv.id if inv else None,
        "investigation_external_id": ctx.get("source_id") or (inv.external_id if inv else "NASA PSI"),
        "investigation_title": inv.title if inv else ctx.get("investigation", ""),
        "publisher": "NASA PSI",
        "doi": inv.doi if inv else None,
        "source_url": r.get("source_link") or (inv.source_url if inv else ""),
        "source_file_name": sf_name,
        "source_file_checksum": sf_sha,
        "combustion_domain": db_run.combustion_domain if db_run else "unknown",
        "gravity_regime": ctx.get("gravity_level") or (db_run.gravity_regime if db_run else "unknown"),
        "is_terrestrial_baseline": is_baseline or (ctx.get("gravity_level") == "normal_gravity"),
        "platform": ctx.get("platform") or (db_run.platform if db_run else "ISS"),
        "fuel_material": db_run.fuel_material if db_run else (ctx.get("fuel") or "Unknown"),
        "oxygen_fraction": db_run.oxygen_fraction if db_run else None,
        "pressure_normalized_kpa": db_run.pressure_normalized_kpa if db_run else None,
        "pressure_original": f"{db_run.pressure_value} {db_run.pressure_unit}" if (db_run and db_run.pressure_value is not None) else None,
        "flow_velocity_normalized_cm_s": db_run.flow_velocity_normalized_cm_s if db_run else None,
        "flow_velocity_original": f"{db_run.flow_velocity_value} {db_run.flow_velocity_unit}" if (db_run and db_run.flow_velocity_value is not None) else None,
        "distance_d": r["distance"],
        "condition_closeness_index": round(r["score"] * 100.0, 1),
        "feature_coverage_ratio": r["coverage"],
        "missing_features": missing_features,
        "feature_breakdown": feature_breakdown,
        "outcomes": outcomes,
        "explanation": r["explanation"],
    }
    if is_baseline:
        item["baseline_separation_note"] = (
            "Isolated in Normal-Gravity (1g) Baseline Track: Earth 1g tests experience buoyant convection "
            "and are kept separate from ISS microgravity (0g) rankings."
        )
    return item


def run_domain_gated_comparison(db: Session, req: CompareRequest) -> Dict[str, Any]:
    """
    Execute similarity ranking using the team's flare_ranking engine (adapter.py + ranking.py)
    on the full FLARE_AI_Data_Handoff dataset.
    """
    table, _issues = get_ranking_table()
    ranking_domain = API_TO_RANKING_DOMAIN.get(req.target_domain, req.target_domain)

    # Convert API canonical inputs -> flare_ranking inputs (o2_percent, pressure_psi, airflow_cm_s)
    weights_mapped = {
        "o2_percent": float(req.weights.get("oxygen_fraction", 0.45)),
        "pressure_psi": float(req.weights.get("pressure_kpa", 0.25)),
        "airflow_cm_s": float(req.weights.get("flow_velocity_cm_s", 0.30)),
    }

    query_mg = {
        "domain": ranking_domain,
        "gravity": req.target_gravity if req.target_gravity in ("microgravity", "normal_gravity") else "microgravity",
        "o2_percent": round(req.oxygen_fraction * 100.0, 2),
        "pressure_psi": round(req.pressure_kpa * KPA_TO_PSI, 3),
        "airflow_cm_s": req.flow_velocity_cm_s,
    }

    res_mg = rank_experiments(table, query_mg, weights=weights_mapped, top_k=25, min_coverage=0.25)

    # Also query normal_gravity baseline track in the same domain if requested
    res_1g = None
    if req.include_terrestrial_baseline:
        query_1g = dict(query_mg)
        query_1g["gravity"] = "normal_gravity"
        res_1g = rank_experiments(table, query_1g, weights=weights_mapped, top_k=15, min_coverage=0.25)

    # Fetch matching DB ExperimentRuns for outcomes & metadata
    all_codes = [r["experiment_id"] for r in res_mg.get("results", [])]
    if res_1g:
        all_codes += [r["experiment_id"] for r in res_1g.get("results", [])]

    db_runs = (
        db.query(ExperimentRun)
        .options(
            selectinload(ExperimentRun.measurements),
            selectinload(ExperimentRun.investigation).selectinload(Investigation.source_files),
        )
        .filter(ExperimentRun.run_code.in_(all_codes))
        .all()
        if all_codes
        else []
    )
    db_runs_by_code = {r.run_code: r for r in db_runs}

    compatible_ranked = [
        _format_ranking_item(r, db_runs_by_code, is_baseline=False)
        for r in res_mg.get("results", [])
    ]
    baseline_ranked = (
        [_format_ranking_item(r, db_runs_by_code, is_baseline=True) for r in res_1g.get("results", [])]
        if res_1g
        else []
    )

    # Sample excluded incompatible-domain runs from DB for the Domain Gate Audit panel
    incompatible_runs = (
        db.query(ExperimentRun)
        .options(selectinload(ExperimentRun.investigation))
        .filter(ExperimentRun.combustion_domain != req.target_domain)
        .limit(12)
        .all()
    )
    excluded_incompatible = [
        {
            "run_id": r.id,
            "run_code": r.run_code,
            "investigation_external_id": r.investigation.external_id if r.investigation else "UNKNOWN",
            "investigation_title": r.investigation.title if r.investigation else "",
            "record_domain": r.combustion_domain,
            "target_domain": req.target_domain,
            "gravity_regime": r.gravity_regime,
            "fuel_material": r.fuel_material,
            "rejection_reason": (
                f"Blocked by Domain Gate: Record domain '{r.combustion_domain}' is incompatible with "
                f"target domain '{req.target_domain}'."
            ),
        }
        for r in incompatible_runs
    ]

    return {
        "scientific_disclaimer": SCIENTIFIC_DISCLAIMER,
        "formula": "D(S, E_i) = sqrt( sum(w_k * |x_k - q_k|^2) / sum(w_k) ); Score = (1 - D) * coverage",
        "scaler_audit": {
            "scaler_type": "flare_ranking MinMax Domain Span Normalization + Coverage Weighting (adapter.py + ranking.py)",
            "feature_spans": {
                "o2_percent": {"min": 0.0, "max": 100.0, "unit": "% vol"},
                "pressure_psi": {"min": 0.0, "max": 50.0, "unit": "psi"},
                "airflow_cm_s": {"min": 0.0, "max": 100.0, "unit": "cm/s"},
            },
            "normalized_weights": weights_mapped,
            "target_conditions": {
                "target_domain": req.target_domain,
                "target_gravity": req.target_gravity,
                "oxygen_fraction": req.oxygen_fraction,
                "pressure_kpa": req.pressure_kpa,
                "flow_velocity_cm_s": req.flow_velocity_cm_s,
            },
            "ranking_notes": res_mg.get("notes", []),
            "n_candidates_in_domain": res_mg.get("n_candidates", 0),
            "n_excluded_by_domain_or_gravity": res_mg.get("n_excluded_by_domain_or_gravity", 0),
        },
        "compatible_microgravity_ranking": compatible_ranked,
        "terrestrial_baseline_track": baseline_ranked,
        "excluded_incompatible_domains": excluded_incompatible,
    }
