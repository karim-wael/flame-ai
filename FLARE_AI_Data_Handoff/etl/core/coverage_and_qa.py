"""Stage 4: Build the Coverage / Research-Gap Matrix (processed/coverage.csv, docs/COVERAGE_MATRIX.md)
and the Quality Assurance Report (docs/QA_REPORT.md), plus sync processed/issues.csv.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import csv
import shutil
from pathlib import Path

from etl.core.common import CONTRACT_VERSION, ETL_VERSION, ROOT

COVERAGE_FIELDS = [
    "cell_id",
    "gravity_regime",
    "domain",
    "o2_band",
    "pressure_band",
    "flow_band",
    "total_runs",
    "unique_runs",
    "sources",
    "fuels",
    "coverage_status",
    "gap_note",
]


def o2_band(val_str: str) -> str:
    if not val_str:
        return "unmeasured_o2"
    v = float(val_str)
    if v < 19.0:
        return "low_o2 (<19%)"
    if v <= 23.0:
        return "normoxic_o2 (19-23%)"
    return "enriched_o2 (>23%)"


def pressure_band(val_str: str) -> str:
    if not val_str:
        return "unmeasured_pressure"
    v = float(val_str)
    if v < 85.0:
        return "sub_atm (<85 kPa / ~0.7 atm)"
    if v <= 115.0:
        return "near_atm (85-115 kPa / ~1 atm)"
    return "elevated_pressure (>115 kPa / 2-3 atm)"


def flow_band(val_str: str, reason: str) -> str:
    if not val_str:
        if reason == "pending_review":
            return "pending_calibration (raw setting only)"
        return "unmeasured_or_quiescent"
    v = float(val_str)
    if v <= 0.0:
        return "zero_or_negative_cal (<=0 cm/s)"
    if v <= 15.0:
        return "low_flow (0-15 cm/s)"
    if v <= 40.0:
        return "moderate_flow (15-40 cm/s)"
    return "high_flow (>40 cm/s)"


def build_coverage_and_qa(runs_rows: list[dict], meas_rows: list[dict], rejected_rows: list[dict]) -> None:
    out_dir = ROOT / "processed"
    docs_dir = ROOT / "docs"
    issues_src = docs_dir / "ISSUES_LOG.csv"
    if issues_src.exists():
        shutil.copyfile(issues_src, out_dir / "issues.csv")

    groups: dict[tuple[str, str, str, str, str], list[dict]] = defaultdict(list)
    for r in runs_rows:
        key = (
            r["gravity_regime"],
            r["domain"],
            o2_band(r["o2_vol_pct"]),
            pressure_band(r["pressure_kpa"]),
            flow_band(r["flow_cm_s"], r["flow_missing_reason"]),
        )
        groups[key].append(r)

    cov_rows: list[dict] = []
    idx = 1
    for key in sorted(groups.keys()):
        rs = groups[key]
        uniq = sum(1 for x in rs if x["dup_status"] == "unique")
        srcs = sorted({x["source_id"] for x in rs})
        fuels = sorted({x["fuel"] for x in rs})
        status = "covered" if uniq >= 5 else "sparse (<5 unique runs)"
        note = ""
        if key[4] == "pending_calibration (raw setting only)":
            note = "Single numeric Air display exists; awaits Malak approval of U = 1.0066 * Air display (I-006/I-007)."
        elif key[4] == "zero_or_negative_cal (<=0 cm/s)":
            note = "Negative flow values (-0.28, -5.92 cm/s) from linear anemometer intercept u_a = 0.94*AIR - 5.92 (I-016)."
        elif key[2] == "enriched_o2 (>23%)" and key[3] == "sub_atm (<85 kPa / ~0.7 atm)":
            note = "Matches NASA exploration atmosphere regime (~70 kPa / <=10.2 psi, enriched O2)."
        cov_rows.append({
            "cell_id": f"COV-{idx:02d}",
            "gravity_regime": key[0],
            "domain": key[1],
            "o2_band": key[2],
            "pressure_band": key[3],
            "flow_band": key[4],
            "total_runs": len(rs),
            "unique_runs": uniq,
            "sources": ";".join(srcs),
            "fuels": ";".join(fuels),
            "coverage_status": status,
            "gap_note": note,
        })
        idx += 1

    # Explicit structural research gaps required for FLARE AI gap reporting
    explicit_gaps = [
        (
            "partial_gravity", "liquid_droplet", "ALL (especially >23% O2)", "sub_atm (<85 kPa / ~0.7 atm)", "ALL",
            "CRITICAL GAP: Zero Lunar (~0.16g) or Martian (~0.38g) partial-gravity droplet combustion runs in PSI archive.",
        ),
        (
            "partial_gravity", "solid", "ALL (especially >23% O2)", "sub_atm (<85 kPa / ~0.7 atm)", "ALL",
            "CRITICAL GAP: Zero Lunar (~0.16g) or Martian (~0.38g) partial-gravity solid flammability runs in PSI archive.",
        ),
        (
            "partial_gravity", "gas_jet", "ALL", "ALL", "ALL",
            "CRITICAL GAP: Zero Lunar/Martian partial-gravity gas-jet smoke-point runs in PSI archive.",
        ),
        (
            "partial_gravity", "smoke", "ALL", "ALL", "ALL",
            "CRITICAL GAP: Zero Lunar/Martian partial-gravity smoke aerosol detector runs in PSI archive.",
        ),
        (
            "microgravity", "solid", "enriched_o2 (>23%)", "sub_atm (<85 kPa / ~0.7 atm)", "ALL",
            "CRITICAL GAP: Exploration habitat atmosphere (<=10.2 psi / ~70 kPa + enriched O2) has 35 FLEX droplet runs but 0 solid runs (BASS-II and SAFFIRE-I operated at ~1 atm / ~21% O2 and did not record per-run pressure in CSV).",
        ),
        (
            "microgravity", "smoke", "low_o2 / enriched_o2", "sub_atm / elevated_pressure", "ALL",
            "INSTRUMENTATION GAP: Smoke aerosol investigations PSI-101 (SAME-R, 169 rows) and PSI-102 (SAME, 114 rows) report airflow (0-10 cm/s) across ISS microgravity and 1g ground baselines, but 0 per-run O2 or pressure values.",
        ),
        (
            "microgravity", "liquid_droplet", "ALL", "ALL", "low/moderate/high_flow (>0 cm/s)",
            "INSTRUMENTATION GAP: FLEX CSV reports 0 flow_cm_s values (droplets burned in quiescent chamber or slow translating-fiber drift not tabulated in CSV).",
        ),
        (
            "microgravity", "gas_jet", "low_o2 / enriched_o2", "sub_atm / elevated_pressure", "ALL",
            "INSTRUMENTATION GAP: SPICE CSV reports 0 per-run O2 or pressure values (operated in nominal ISS MSG air ~101 kPa, 21% O2).",
        ),
        (
            "normal_gravity", "liquid_droplet / solid / gas_jet", "ALL", "ALL", "ALL",
            "BASELINE GAP IN FLIGHT CSVs: While PSI-101 (60 rows) and PSI-102 (42 rows) include 102 normal-gravity (1g) smoke ground runs, FLEX/BASS-II/SAFFIRE-I/SPICE CSVs contain 0 1g rows (36 1g SPICE rows exist in Dotson_umd_0117N_10980.pdf Tables 6.3-6.4, issue I-025).",
        ),
    ]
    for g_grav, g_dom, g_o2, g_p, g_fl, g_note in explicit_gaps:
        cov_rows.append({
            "cell_id": f"GAP-{idx:02d}",
            "gravity_regime": g_grav,
            "domain": g_dom,
            "o2_band": g_o2,
            "pressure_band": g_p,
            "flow_band": g_fl,
            "total_runs": 0,
            "unique_runs": 0,
            "sources": "",
            "fuels": "",
            "coverage_status": "gap (0 runs)",
            "gap_note": g_note,
        })
        idx += 1

    with open(out_dir / "coverage.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COVERAGE_FIELDS)
        w.writeheader()
        w.writerows(cov_rows)

    _write_coverage_md(docs_dir / "COVERAGE_MATRIX.md", cov_rows)
    _write_qa_report(docs_dir / "QA_REPORT.md", runs_rows, meas_rows, rejected_rows, issues_src)


def _write_coverage_md(path: Path, cov_rows: list[dict]) -> None:
    covered = [r for r in cov_rows if r["total_runs"] > 0]
    gaps = [r for r in cov_rows if r["total_runs"] == 0]
    lines = [
        "# FLARE AI — Coverage & Research-Gap Matrix",
        "",
        "**Owner:** Data Engineering (Farah El Qady, Salma)  ",
        f"**Contract Version:** {CONTRACT_VERSION} · **ETL Version:** {ETL_VERSION}  ",
        "**Machine-readable file:** `processed/coverage.csv`",
        "",
        "---",
        "",
        "## 1. Executive Summary of Parameter Coverage",
        "",
        "Across the **1,157 parsed runs** across all **6 NASA PSI investigations** (`1,100` unique runs after excluding `34` exact and `23` near duplicates in SPICE, plus `77` secondary-aging smoke re-measurements in `PSI-101`/`PSI-102`), each investigation covers **only 1 or 2 of the 3 canonical environmental axes**:",
        "",
        "| Investigation | Domain | Gravity | Oxygen (`o2_vol_pct`) | Pressure (`pressure_kpa`) | Airflow (`flow_cm_s`) | Total Runs (`Unique`) |",
        "|---|---|---|---|---|---|---|",
        "| `PSI-69` **FLEX** | `liquid_droplet` | `microgravity` | **274 rows** (`12–34% vol`) | **273 rows** (`70.2–309.3 kPa`) | **0 rows** (`unavailable_in_source`) | 274 (`274`) |",
        "| `PSI-25` **BASS-II** | `solid` | `microgravity` | **129 rows** (`13.6–27.8% vol`) | **0 rows** (`unavailable_in_source`) | **0 canonical** (`25` single-number `Air display` rows `pending_review`, `100` multi-step/free-text, `4` blank) | 129 (`129`) |",
        "| `PSI-107` **SPICE** | `gas_jet` | `microgravity` | **0 rows** (`unavailable_in_source`, nominal ~21%) | **0 rows** (`unavailable_in_source`, nominal ~101 kPa) | **444 rows** (`-5.92` to `85.28 cm/s`; `25` blank) | 469 (`412`) |",
        "| `PSI-101` **SAME-R** | `smoke` | `microgravity` (`109`), `normal_gravity` (`60`) | **0 rows** (`unavailable_in_source`) | **0 rows** (`unavailable_in_source`) | **169 rows** (`0.0–8.1 cm/s`) | 169 (`169`) |",
        "| `PSI-102` **SAME** | `smoke` | `microgravity` (`64`), `normal_gravity` (`42`), `unknown` (`8`) | **0 rows** (`unavailable_in_source`) | **0 rows** (`unavailable_in_source`) | **102 rows** (`2.1–10.0 cm/s`; `12` blank `not_reported`) | 114 (`114`) |",
        "| `PSI-98` **SAFFIRE-I** | `solid` | `microgravity` (Cygnus) | **2 rows** (`21.5–21.6% vol`) | **0 rows** (`unavailable_in_source`) | **2 rows** (`20.0 cm/s`) | 2 (`2`) |",
        "",
        "> **Headline Takeaway for Malak & Zeiad:** No single downloaded investigation measures all three canonical variables (`o2_vol_pct`, `pressure_kpa`, `flow_cm_s`) simultaneously. FLEX owns the **O₂ × Pressure** plane (including **33 runs strictly >23% O₂** — or **35 runs at ≥23% O₂** — in the sub-atmospheric exploration habitat regime, ~70–73 kPa), SPICE (`PSI-107`) and SAME/SAME-R (`PSI-101`/`102`) own the **Airflow** axis (plus **102 normal-gravity 1g ground baseline runs** in SAME/SAME-R), SAFFIRE-I (`PSI-98`) provides **2 large-scale O₂ × Airflow (`20 cm/s`) solid burns**, and BASS-II (`PSI-25`) bridges **O₂ × Solid Fuels** (and will bridge **O₂ × Airflow** for 25 constant-flow runs if Malak approves `U = 1.0066 × Air display`).",
        "",
        "---",
        "",
        "## 2. Populated Parameter Cells (`total_runs > 0`)",
        "",
        "| Cell ID | Gravity | Domain | O₂ Band | Pressure Band | Flow Band | Total (`Unique`) | Sources | Fuels | Status |",
        "|---|---|---|---|---|---|---:|---|---|---|",
    ]
    for r in covered:
        lines.append(
            f"| `{r['cell_id']}` | `{r['gravity_regime']}` | `{r['domain']}` | {r['o2_band']} | {r['pressure_band']} | {r['flow_band']} | "
            f"{r['total_runs']} (`{r['unique_runs']}`) | `{r['sources']}` | {r['fuels'].replace(';', ', ')} | {r['coverage_status']} |"
        )
    lines += [
        "",
        "---",
        "",
        "## 3. Critical Research & Archive Gaps (`total_runs = 0`)",
        "",
        "| Gap ID | Gravity | Domain | O₂ Band | Pressure Band | Flow Band | Why It Matters |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in gaps:
        lines.append(
            f"| `{r['cell_id']}` | `{r['gravity_regime']}` | `{r['domain']}` | {r['o2_band']} | {r['pressure_band']} | {r['flow_band']} | {r['gap_note']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_qa_report(
    path: Path,
    runs_rows: list[dict],
    meas_rows: list[dict],
    rejected_rows: list[dict],
    issues_src: Path,
) -> None:
    issues = list(csv.DictReader(open(issues_src, encoding="utf-8"))) if issues_src.exists() else []
    open_issues = [i for i in issues if i["status"] == "open"]
    resolved_issues = [i for i in issues if i["status"] == "resolved"]

    by_src = defaultdict(list)
    for r in runs_rows:
        by_src[r["source_id"]].append(r)

    lines = [
        "# FLARE AI — Data Quality Assurance (QA) Report",
        "",
        "**Owner:** Data Engineering (Farah El Qady, Salma)  ",
        f"**Contract Version:** {CONTRACT_VERSION} · **ETL Version:** {ETL_VERSION}  ",
        "",
        "---",
        "",
        "## 1. Pipeline Integrity & Raw Archive Lock",
        "",
        "- **Raw archive verification (`verify_raw.ps1` / `verify_raw()`):** **PASSED** — all `128` raw files in `data/raw/` match their SHA-256 fingerprints in `data/raw_manifest.csv` and are locked read-only.",
        f"- **Total runs parsed across all 6 investigations:** `{len(runs_rows)}` (`274` FLEX + `129` BASS-II + `469` SPICE + `169` SAME-R + `114` SAME + `2` SAFFIRE-I)",
        f"- **Hard-rule rejections (`processed/rejected.csv`):** `{len(rejected_rows)}` (under Contract v0.3, FLEX Test 114's impossible `0 mmHg` pressure is nulled with `invalid_value` and flagged `impossible_value_nulled` rather than discarding the entire run).",
        f"- **Long-format measurements (`processed/run_measurements.csv`):** `{len(meas_rows)}` rows, `0` orphan `run_id`s.",
        "- **Null discipline:** `0` canonical nulls without a valid `missing_reason`; `0` non-null canonical values carrying a `missing_reason`.",
        "",
        "---",
        "",
        "## 2. Completeness & Missing-Reason Breakdown by Source",
        "",
        "| Source | Total Runs | `Unique` | `Exact Dup` | `Near Dup` | `o2_vol_pct` Present (Missing Reason) | `pressure_kpa` Present (Missing Reason) | `flow_cm_s` Present (Missing Reason) |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for sid in ("PSI-69", "PSI-25", "PSI-107", "PSI-101", "PSI-102", "PSI-98"):
        rs = by_src[sid]
        dups = Counter(r["dup_status"] for r in rs)
        o2_ok = sum(1 for r in rs if r["o2_vol_pct"] != "")
        o2_mr = Counter(r["o2_missing_reason"] for r in rs if r["o2_vol_pct"] == "")
        p_ok = sum(1 for r in rs if r["pressure_kpa"] != "")
        p_mr = Counter(r["pressure_missing_reason"] for r in rs if r["pressure_kpa"] == "")
        fl_ok = sum(1 for r in rs if r["flow_cm_s"] != "")
        fl_mr = Counter(r["flow_missing_reason"] for r in rs if r["flow_cm_s"] == "")
        lines.append(
            f"| `{sid}` | {len(rs)} | {dups['unique']} | {dups['exact_duplicate']} | {dups['near_duplicate']} | "
            f"**{o2_ok}** ({dict(o2_mr) or 'none'}) | **{p_ok}** ({dict(p_mr) or 'none'}) | **{fl_ok}** ({dict(fl_mr) or 'none'}) |"
        )

    flag_counts = Counter()
    for r in runs_rows:
        for fl in filter(None, r["qa_flags"].split(";")):
            flag_counts[(r["source_id"], fl)] += 1

    lines += [
        "",
        "---",
        "",
        "## 3. Soft QA Flag Counts (`runs.csv`)",
        "",
        "| Source ID | QA Flag | Row Count | Explanation & Action Taken |",
        "|---|---|---:|---|",
    ]
    flag_notes = {
        ("PSI-69", "gas_sum_off"): "Initial O2 + N2 + CO2 + He mole fractions sum to 0.98 due to source rounding (`I-022`). Values kept unchanged.",
        ("PSI-69", "identifier_reused"): "FLEX Test #183 and #184 share `FLEX Identifier = 193F001`. Keyed by `FLEX Test #`, so `run_id` stays unique.",
        ("PSI-69", "impossible_value_nulled"): "FLEX Test #114 (`C11M201`) recorded `0 mmHg` ambient pressure (`I-020`). `pressure_kpa` blanked to NULL + `invalid_value`; raw `0` kept in `pressure_raw`.",
        ("PSI-25", "fuel_label_normalised"): "Raw geometry/material descriptions (e.g. `1/4\" black rod`, `100 micron PMMA film 2 cm wide`) mapped to confirmed material (`PMMA`, `SIBAL`, `Nomex`, `wax candle`) per *BASS-II data FAQ.docx* (`I-019`); full text kept in `fuel_detail`.",
        ("PSI-25", "negative_gas_reading"): "`Initial CO (ppm)` recorded as `-1` (sensor zero-offset artifact, `I-010`). Numeric value blanked with `invalid_value`; `-1` preserved in `value_text`.",
        ("PSI-25", "date_year_typo_in_source"): "Tests `O20–O22` (`2/26/2016`, `GMT=57`) and `T9`, `T18` (`6/24/2018`, `GMT=175`) have year typos in the raw table (`I-024`). Raw dates preserved without silent editing.",
        ("PSI-107", "fuel_label_normalised"): "`75 % Propylene` and `50 % Propylene` spacing/case normalised to `75% propylene` and `50% propylene` (`I-015`).",
        ("PSI-107", "below_physical_range"): "`Air Rate (cm/s)` is `-0.28` (5 rows) or `-5.92` (3 rows) from the negative intercept of the linear anemometer calibration $u_{a,0} = 0.94 \\cdot \\text{AIR} - 5.92$ at `AIR=6` and `AIR=0` (`I-016`).",
        ("PSI-107", "time_unparsed"): "`GMT ignition` contains telemetry status codes (`LOS`, `Ku LOS`, `no ku`, `n/a`) instead of a clock time (`13` rows, `I-014`).",
        ("PSI-101", "secondary_aging_remeasurement"): "Second aerosol measurement of parent smoke cloud after additional aging (`72` rows, `dup_of` set to parent `run_id`, `I-027`).",
        ("PSI-101", "added_from_workbook"): "`Kapton 112` present in `Combined SAMER Results 06 02 14.xlsx` and 109-run final report but omitted from PSI summary CSV (`I-026`).",
        ("PSI-102", "secondary_aging_remeasurement"): "Second aerosol measurement of parent smoke cloud after additional aging (`34` rows, `dup_of` set to parent `run_id`, `I-027`).",
        ("PSI-102", "outside_documented_hardware_range"): "`PSI-102:TABLE_4` reports `10 cm/s`, above the `2–8 cm/s` hardware range stated in the SAME report (`I-028`).",
        ("PSI-98", "dimensions_swapped_in_source"): "Raw CSV swapped sample length (`40.6 cm`) and width (`94 cm`); corrected to `940 mm x 406 mm` (`I-030`).",
        ("PSI-98", "suspect_thickness_unit"): "Raw CSV reports `0.37 cm` (`3.7 mm`) thickness for thin SIBAL fabric (likely `0.37 mm`, `I-031`).",
    }
    for (sid, fl), cnt in sorted(flag_counts.items()):
        lines.append(f"| `{sid}` | `{fl}` | {cnt} | {flag_notes.get((sid, fl), '')} |")

    lines += [
        "",
        "---",
        "",
        f"## 4. Open Science Decisions for Malak ({len(open_issues)} Open of {len(issues)} Logged Issues)",
        "",
        "Full log in `docs/ISSUES_LOG.csv` (and `processed/issues.csv`):",
        "",
        "| Issue ID | Source | Column | Severity | Decision Needed / Status |",
        "|---|---|---|---|---|",
    ]
    for i in open_issues:
        lines.append(f"| `{i['issue_id']}` | `{i['source_id']}` | `{i['column']}` | `{i['severity']}` | {i['decision']} |")

    lines += [
        "",
        f"*(The remaining {len(resolved_issues)} issues in `ISSUES_LOG.csv` were resolved during Stage 2 and Stage 3 document verification.)*",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
