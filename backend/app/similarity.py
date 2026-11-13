import math
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .config import SCIENTIFIC_DISCLAIMER
from .models import ExperimentRun, Investigation, SourceFile
from .schemas import CompareRequest

# Canonical physiological/spacecraft normalization spans for min-max scaling
FEATURE_SPANS = {
    "oxygen_fraction": {"min": 0.15, "max": 0.35, "unit": "fraction (0-1)"},
    "pressure_kpa": {"min": 50.0, "max": 130.0, "unit": "kPa"},
    "flow_velocity_cm_s": {"min": 0.0, "max": 60.0, "unit": "cm/s"},
}

DOMAIN_EXPLANATIONS = {
    "solid": "Solid-fuel surface pyrolysis and boundary-layer flame spread (e.g., PMMA, SIBAL cloth).",
    "gas": "Gaseous laminar co-flow diffusion jet combustion and soot smoke-point kinetics (e.g., SPICE C2H4/C3H8/CH4).",
    "liquid_droplet": "Spherical liquid droplet d²-law vaporization or 3D droplet cloud percolation (e.g., FLEX, JAXA Kibo GCE).",
    "aerosol_smoke": "Non-flaming thermal pyrolysis smoke aerosol generation and particle coagulation (e.g., SAME / SAME-R).",
}


def scale_delta(val_a: float, val_b: float, feature_key: str) -> float:
    span_info = FEATURE_SPANS[feature_key]
    span = span_info["max"] - span_info["min"]
    if span <= 0:
        return 0.0
    return abs(val_a - val_b) / span


def run_domain_gated_comparison(db: Session, req: CompareRequest) -> Dict[str, Any]:
    """
    Execute Section 7 Scientific Comparison Rules:
    - Enforce combustion domain gate before calculating distance.
    - Separate Earth-based FSRI / 1g baseline records from microgravity rankings.
    - Never impute missing values to zero; surface missing_reason explicitly.
    - Compute weighted normalized Euclidean distance D(S, E_i) and explain the score.
    """
    all_runs: List[ExperimentRun] = db.query(ExperimentRun).all()
    if req.candidate_run_ids:
        allowed_set = set(req.candidate_run_ids)
        all_runs = [r for r in all_runs if r.id in allowed_set or r.run_code in allowed_set]

    w1 = float(req.weights.get("oxygen_fraction", 0.45))
    w2 = float(req.weights.get("pressure_kpa", 0.25))
    w3 = float(req.weights.get("flow_velocity_cm_s", 0.30))
    w_sum = w1 + w2 + w3
    if w_sum <= 0:
        w1, w2, w3, w_sum = 0.45, 0.25, 0.30, 1.0
    norm_weights = {
        "oxygen_fraction": round(w1 / w_sum, 4),
        "pressure_kpa": round(w2 / w_sum, 4),
        "flow_velocity_cm_s": round(w3 / w_sum, 4),
    }

    compatible_ranked: List[Dict[str, Any]] = []
    terrestrial_baseline_track: List[Dict[str, Any]] = []
    excluded_incompatible: List[Dict[str, Any]] = []

    for run in all_runs:
        inv: Investigation = run.investigation
        sf_list: List[SourceFile] = inv.source_files if inv else []
        primary_sf = sf_list[0] if sf_list else None

        # 1. Domain Gate Check
        if run.combustion_domain != req.target_domain:
            excluded_incompatible.append({
                "run_id": run.id,
                "run_code": run.run_code,
                "investigation_external_id": inv.external_id if inv else "UNKNOWN",
                "investigation_title": inv.title if inv else "",
                "record_domain": run.combustion_domain,
                "target_domain": req.target_domain,
                "gravity_regime": run.gravity_regime,
                "fuel_material": run.fuel_material,
                "rejection_reason": (
                    f"Blocked by Domain Gate: Record domain '{run.combustion_domain}' "
                    f"({DOMAIN_EXPLANATIONS.get(run.combustion_domain, 'different physics')}) "
                    f"is physically incompatible with target domain '{req.target_domain}'."
                ),
            })
            continue

        # 2. Compute Feature Deltas & Handle Missingness Explicitly (Never convert NULL to 0)
        missing_features: List[Dict[str, str]] = []
        available_weight = 0.0
        weighted_sq_sum = 0.0
        feature_breakdown: Dict[str, Any] = {}

        # Feature 1: Oxygen Fraction
        if run.oxygen_fraction is not None:
            d_o2 = scale_delta(req.oxygen_fraction, run.oxygen_fraction, "oxygen_fraction")
            contrib_o2 = norm_weights["oxygen_fraction"] * (d_o2 ** 2)
            weighted_sq_sum += contrib_o2
            available_weight += norm_weights["oxygen_fraction"]
            feature_breakdown["oxygen_fraction"] = {
                "status": "measured",
                "target": req.oxygen_fraction,
                "record_value": run.oxygen_fraction,
                "unit": "fraction",
                "raw_delta": round(abs(req.oxygen_fraction - run.oxygen_fraction), 4),
                "scaled_delta": round(d_o2, 4),
                "weighted_sq_term": round(contrib_o2, 5),
            }
        else:
            reason = run.oxygen_missing_reason or "not_reported"
            missing_features.append({"feature": "oxygen_fraction", "missing_reason": reason})
            feature_breakdown["oxygen_fraction"] = {
                "status": "missing",
                "missing_reason": reason,
                "note": "Explicitly preserved as NULL; never assumed or zero-filled.",
            }

        # Feature 2: Pressure (Normalized kPa)
        if run.pressure_normalized_kpa is not None:
            d_p = scale_delta(req.pressure_kpa, run.pressure_normalized_kpa, "pressure_kpa")
            contrib_p = norm_weights["pressure_kpa"] * (d_p ** 2)
            weighted_sq_sum += contrib_p
            available_weight += norm_weights["pressure_kpa"]
            feature_breakdown["pressure_kpa"] = {
                "status": "measured",
                "target": req.pressure_kpa,
                "record_value": run.pressure_normalized_kpa,
                "original_value": run.pressure_value,
                "original_unit": run.pressure_unit,
                "normalized_unit": "kPa",
                "raw_delta": round(abs(req.pressure_kpa - run.pressure_normalized_kpa), 2),
                "scaled_delta": round(d_p, 4),
                "weighted_sq_term": round(contrib_p, 5),
            }
        else:
            reason = run.pressure_missing_reason or "not_reported"
            missing_features.append({"feature": "pressure_kpa", "missing_reason": reason})
            feature_breakdown["pressure_kpa"] = {
                "status": "missing",
                "missing_reason": reason,
                "note": "Explicitly preserved as NULL; never assumed or zero-filled.",
            }

        # Feature 3: Flow Velocity (Normalized cm/s)
        if run.flow_velocity_normalized_cm_s is not None:
            d_v = scale_delta(req.flow_velocity_cm_s, run.flow_velocity_normalized_cm_s, "flow_velocity_cm_s")
            contrib_v = norm_weights["flow_velocity_cm_s"] * (d_v ** 2)
            weighted_sq_sum += contrib_v
            available_weight += norm_weights["flow_velocity_cm_s"]
            feature_breakdown["flow_velocity_cm_s"] = {
                "status": "measured",
                "target": req.flow_velocity_cm_s,
                "record_value": run.flow_velocity_normalized_cm_s,
                "original_value": run.flow_velocity_value,
                "original_unit": run.flow_velocity_unit,
                "normalized_unit": "cm/s",
                "raw_delta": round(abs(req.flow_velocity_cm_s - run.flow_velocity_normalized_cm_s), 2),
                "scaled_delta": round(d_v, 4),
                "weighted_sq_term": round(contrib_v, 5),
            }
        else:
            reason = run.flow_velocity_missing_reason or "unavailable_in_source"
            missing_features.append({"feature": "flow_velocity_cm_s", "missing_reason": reason})
            feature_breakdown["flow_velocity_cm_s"] = {
                "status": "missing",
                "missing_reason": reason,
                "note": "Explicitly preserved as NULL; never assumed or zero-filled.",
            }

        # Re-normalize by available feature weight and apply transparent uncertainty penalty if any feature is missing
        if available_weight > 0:
            adjusted_sq = weighted_sq_sum / available_weight
            raw_distance = math.sqrt(adjusted_sq)
        else:
            raw_distance = 1.0

        # Relevance index in [0, 100] strictly representing closeness of experimental conditions
        coverage_ratio = round(available_weight, 2)
        closeness_score = max(0.0, round(100.0 * (1.0 / (1.0 + 2.2 * raw_distance)) * (0.85 + 0.15 * coverage_ratio), 1))

        outcomes_summary = [
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
                "uncertainty": m.uncertainty,
            }
            for m in run.measurements
        ]

        explanation_parts = [
            f"Domain matched ('{run.combustion_domain}').",
            f"Weighted distance D(S, E_i) = {raw_distance:.4f} across {len( [k for k in feature_breakdown.values() if k['status']=='measured'] )}/3 validated condition variables.",
        ]
        if missing_features:
            miss_str = ", ".join(f"{m['feature']} ({m['missing_reason']})" for m in missing_features)
            explanation_parts.append(f"Explicit missingness preserved without zero-imputation: {miss_str}.")

        entry = {
            "run_id": run.id,
            "run_code": run.run_code,
            "investigation_id": inv.id if inv else None,
            "investigation_external_id": inv.external_id if inv else "UNKNOWN",
            "investigation_title": inv.title if inv else "",
            "publisher": inv.source.publisher if (inv and inv.source) else "NASA PSI",
            "doi": inv.doi if inv else None,
            "source_url": inv.source_url if inv else "",
            "source_file_name": primary_sf.file_name if primary_sf else None,
            "source_file_checksum": primary_sf.checksum_sha256 if primary_sf else None,
            "combustion_domain": run.combustion_domain,
            "gravity_regime": run.gravity_regime,
            "is_terrestrial_baseline": run.is_terrestrial_baseline,
            "platform": run.platform,
            "fuel_material": run.fuel_material,
            "oxygen_fraction": run.oxygen_fraction,
            "pressure_normalized_kpa": run.pressure_normalized_kpa,
            "pressure_original": f"{run.pressure_value} {run.pressure_unit}" if run.pressure_value is not None else None,
            "flow_velocity_normalized_cm_s": run.flow_velocity_normalized_cm_s,
            "flow_velocity_original": f"{run.flow_velocity_value} {run.flow_velocity_unit}" if run.flow_velocity_value is not None else None,
            "distance_d": round(raw_distance, 4),
            "condition_closeness_index": closeness_score,
            "feature_coverage_ratio": coverage_ratio,
            "missing_features": missing_features,
            "feature_breakdown": feature_breakdown,
            "outcomes": outcomes_summary,
            "explanation": " ".join(explanation_parts),
        }

        # 3. Separate Earth-based FSRI / 1g baseline from microgravity ranking
        if run.is_terrestrial_baseline or run.gravity_regime != req.target_gravity:
            entry["baseline_separation_note"] = (
                "Isolated in Terrestrial / Alternate-Gravity Baseline Track: Earth 1g tests experience strong buoyant "
                "plume convection (~45-55 cm/s) and are not interchangeable with ISS microgravity measurements."
            )
            if req.include_terrestrial_baseline:
                terrestrial_baseline_track.append(entry)
        else:
            compatible_ranked.append(entry)

    compatible_ranked.sort(key=lambda x: (x["distance_d"], -x["feature_coverage_ratio"]))
    for idx, item in enumerate(compatible_ranked, start=1):
        item["rank"] = idx

    terrestrial_baseline_track.sort(key=lambda x: x["distance_d"])

    return {
        "scientific_disclaimer": SCIENTIFIC_DISCLAIMER,
        "formula": "D(S, E_i) = sqrt( w1 * (ΔO2_norm)^2 + w2 * (ΔP_norm)^2 + w3 * (ΔVair_norm)^2 )",
        "scaler_audit": {
            "scaler_type": "Canonical Unit Conversion + MinMax Domain Span Normalization",
            "feature_spans": FEATURE_SPANS,
            "normalized_weights": norm_weights,
            "target_conditions": {
                "target_domain": req.target_domain,
                "target_gravity": req.target_gravity,
                "oxygen_fraction": req.oxygen_fraction,
                "pressure_kpa": req.pressure_kpa,
                "flow_velocity_cm_s": req.flow_velocity_cm_s,
            },
        },
        "compatible_microgravity_ranking": compatible_ranked,
        "terrestrial_baseline_track": terrestrial_baseline_track,
        "excluded_incompatible_domains": excluded_incompatible,
    }
