"""Adapters for Salma's three preprocessed PSI investigations:
  - PSI-101 (SAME-R): 169 runs (109 ISS microgravity + 60 ground 1g)
  - PSI-102 (SAME):   114 runs (64 ISS microgravity + 42 ground 1g + 8 summary table rows)
  - PSI-98  (SAFFIRE-I): 2 large-scale SIBAL solid burns on free-flying Cygnus OA-6

Reconciles Salma's wide CSV outputs into the canonical 36-column runs.csv +
7-column run_measurements.csv contract (DATA_CONTRACT.md v0.3).
"""
from __future__ import annotations

from dataclasses import dataclass
from etl.core.common import Run, clean_text, fmt, new_run, parse_num, read_raw_table

PLATFORM_MAP = {
    "International Space Station (ISS)": "ISS",
    "ground (NASA GRC)": "ground",
    "Cygnus cargo vehicle after leaving ISS (free-flying)": "Cygnus",
    "": "unknown",
}

DOMAIN_MAP = {
    "aerosol_smoke": "smoke",
    "solid": "solid",
}

SMOKE_MEAS_COLS = [
    ("rt_r0", "rt_r0", "ratio"),
    ("heater_temp_c_derived", "heater_temp_c_derived", "degC"),
    ("heating_duration_s", "heating_duration_s", "s"),
    ("primary_aging_s", "primary_aging_s", "s"),
    ("primary_mixing_s", "primary_mixing_s", "s"),
    ("net_aging_s", "net_aging_s", "s"),
    ("net_aging_s_workbook", "net_aging_s_workbook", "s"),
    ("aging_duration_s", "aging_duration_s", "s"),
    ("weight_loss_rate_mg_min", "weight_loss_rate_mg_min", "mg/min"),
    ("mass_loss_mg", "mass_loss_mg", "mg"),
    ("amd_um", "amd_um", "um"),
    ("dam_um", "dam_um", "um"),
    ("dam_dusttrak_a_um", "dam_dusttrak_a_um", "um"),
    ("dam_dusttrak_b_um", "dam_dusttrak_b_um", "um"),
    ("cmd_um", "cmd_um", "um"),
    ("hc_sigma_g", "hc_sigma_g", "unitless"),
    ("hc_dg_um", "hc_dg_um", "um"),
    ("m0_per_cm3", "m0_per_cm3", "1/cm3"),
    ("m1_mm_per_cm3", "m1_mm_per_cm3", "mm/cm3"),
]

SAFFIRE_MEAS_COLS = [
    ("o2_vol_pct_low", "o2_vol_pct_low", "% vol"),
    ("o2_vol_pct_high", "o2_vol_pct_high", "% vol"),
    ("ignition_power_w", "ignition_power_w", "W"),
    ("ignition_time_s", "ignition_time_s", "s"),
    ("burn_time_s", "burn_time_s", "s"),
    ("sample_thickness_mm", "sample_thickness_mm", "mm"),
    ("sample_length_mm", "sample_length_mm", "mm"),
    ("sample_width_mm", "sample_width_mm", "mm"),
]


def _norm_key(source_id: str, code: str) -> str:
    prefix = f"{source_id}_"
    return code[len(prefix) :] if code.startswith(prefix) else code


def _parse_salma_table(source_id: str, investigation: str, rel_table: str) -> list[Run]:
    rows, headers, sha = read_raw_table(rel_table, "utf-8")
    runs: list[Run] = []

    for i, row in enumerate(rows, start=1):
        raw_code = clean_text(row["run_code"])
        native_key = _norm_key(source_id, raw_code)
        parent_raw = clean_text(row.get("parent_run_code", ""))
        parent_id = f"{source_id}:{_norm_key(source_id, parent_raw)}" if parent_raw else ""

        domain = DOMAIN_MAP[clean_text(row["domain"])]
        platform = PLATFORM_MAP.get(clean_text(row["platform"]), "unknown")
        gravity = clean_text(row["gravity_regime"]) or "unknown"

        t_date = clean_text(row["test_date"])
        mat = clean_text(row["material"])
        desc = clean_text(row["description"])
        notes = clean_text(row.get("notes", ""))
        detail_parts = [x for x in (desc, notes) if x]
        fuel_detail = " | ".join(detail_parts)

        # Oxygen
        o2_val, _ = parse_num(row.get("o2_vol_pct", ""))
        o2_raw = clean_text(row.get("o2_raw", ""))
        if o2_val is not None:
            o2_basis = "approximate" if "~" in o2_raw else ("range_midpoint" if "-" in o2_raw else "nominal")
            o2_reason = ""
            o2_unit = "% vol"
        else:
            o2_basis = ""
            o2_reason = "unavailable_in_source"
            o2_unit = ""

        # Pressure (unavailable in all 3 sources)
        p_reason = "unavailable_in_source"

        # Flow
        fl_val, _ = parse_num(row.get("flow_cm_s", ""))
        fl_raw = clean_text(row.get("flow_cm_s_raw", ""))
        fl_unit = clean_text(row.get("flow_unit_raw", "")) if fl_val is not None else ""
        fl_basis = clean_text(row.get("flow_definition", "")) if fl_val is not None else ""
        fl_reason = "" if fl_val is not None else "not_reported"

        d = new_run(
            source_id,
            investigation,
            native_key,
            f"data/raw/{rel_table}",
            sha,
            i,
            native_test_id=clean_text(row.get("source_test_id", "")),
            domain=domain,
            platform=platform,
            gravity_regime=gravity,
            test_date=t_date,
            test_date_raw=t_date,
            fuel_raw=mat,
            fuel=mat,
            fuel_detail=fuel_detail,
            o2_vol_pct=fmt(o2_val),
            o2_basis=o2_basis,
            o2_missing_reason=o2_reason,
            o2_raw=o2_raw,
            o2_raw_unit=o2_unit,
            pressure_missing_reason=p_reason,
            flow_cm_s=fmt(fl_val),
            flow_basis=fl_basis,
            flow_missing_reason=fl_reason,
            flow_raw=fl_raw,
            flow_raw_unit=fl_unit,
            dup_of=parent_id,
        )

        # Use unique raw_cells tuple per row so mark_duplicates doesn't overwrite secondary-aging dup_of
        r = Run(d, raw_cells=(raw_code,) + tuple(row[h] for h in headers))

        if clean_text(row.get("is_secondary_aging", "")).lower() == "true":
            r.flag("secondary_aging_remeasurement")
        if clean_text(row.get("data_origin", "")) == "workbook_only":
            r.flag("added_from_workbook")
        if source_id == "PSI-102" and fl_val is not None and fl_val > 8.0:
            r.flag("outside_documented_hardware_range")
        if source_id == "PSI-98":
            r.flag("dimensions_swapped_in_source")
            r.flag("suspect_thickness_unit")
            r.measure(row, "flow_direction", "flow_direction", None, numeric=False)
            for col, var, unit in SAFFIRE_MEAS_COLS:
                if clean_text(row.get(col, "")) != "":
                    r.measure(row, col, var, unit)
        else:
            for col, var, unit in SMOKE_MEAS_COLS:
                if clean_text(row.get(col, "")) != "":
                    r.measure(row, col, var, unit)

        runs.append(r)

    return runs


@dataclass
class _SalmaAdapter:
    SOURCE_ID: str
    INVESTIGATION: str
    TABLE: str

    def parse(self) -> list[Run]:
        return _parse_salma_table(self.SOURCE_ID, self.INVESTIGATION, self.TABLE)


samer = _SalmaAdapter("PSI-101", "SAME-R", "PSI-101_SAME-R/PSI-101_runs.csv")
same = _SalmaAdapter("PSI-102", "SAME", "PSI-102_SAME/PSI-102_runs.csv")
saffire1 = _SalmaAdapter("PSI-98", "SAFFIRE-I", "PSI-98_SAFFIRE-I/PSI-98_runs.csv")
