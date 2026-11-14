# FLARE AI — Data Quality Assurance (QA) Report

**Owner:** Data Engineering (Farah El Qady, Salma)  
**Contract Version:** v0.3 · **ETL Version:** 0.1.0  

---

## 1. Pipeline Integrity & Raw Archive Lock

- **Raw archive verification (`verify_raw.ps1` / `verify_raw()`):** **PASSED** — all `128` raw files in `data/raw/` match their SHA-256 fingerprints in `data/raw_manifest.csv` and are locked read-only.
- **Total runs parsed across all 6 investigations:** `1157` (`274` FLEX + `129` BASS-II + `469` SPICE + `169` SAME-R + `114` SAME + `2` SAFFIRE-I)
- **Hard-rule rejections (`processed/rejected.csv`):** `0` (under Contract v0.3, FLEX Test 114's impossible `0 mmHg` pressure is nulled with `invalid_value` and flagged `impossible_value_nulled` rather than discarding the entire run).
- **Long-format measurements (`processed/run_measurements.csv`):** `10079` rows, `0` orphan `run_id`s.
- **Null discipline:** `0` canonical nulls without a valid `missing_reason`; `0` non-null canonical values carrying a `missing_reason`.

---

## 2. Completeness & Missing-Reason Breakdown by Source

| Source | Total Runs | `Unique` | `Exact Dup` | `Near Dup` | `o2_vol_pct` Present (Missing Reason) | `pressure_kpa` Present (Missing Reason) | `flow_cm_s` Present (Missing Reason) |
|---|---:|---:|---:|---:|---|---|---|
| `PSI-69` | 274 | 274 | 0 | 0 | **274** (none) | **273** ({'invalid_value': 1}) | **0** ({'unavailable_in_source': 274}) |
| `PSI-25` | 129 | 129 | 0 | 0 | **129** (none) | **0** ({'unavailable_in_source': 129}) | **0** ({'pending_review': 25, 'not_parseable': 100, 'not_reported': 4}) |
| `PSI-107` | 469 | 412 | 34 | 23 | **0** ({'unavailable_in_source': 469}) | **0** ({'unavailable_in_source': 469}) | **444** ({'not_reported': 25}) |
| `PSI-101` | 169 | 169 | 0 | 0 | **0** ({'unavailable_in_source': 169}) | **0** ({'unavailable_in_source': 169}) | **169** (none) |
| `PSI-102` | 114 | 114 | 0 | 0 | **0** ({'unavailable_in_source': 114}) | **0** ({'unavailable_in_source': 114}) | **102** ({'not_reported': 12}) |
| `PSI-98` | 2 | 2 | 0 | 0 | **2** (none) | **0** ({'unavailable_in_source': 2}) | **2** (none) |

---

## 3. Soft QA Flag Counts (`runs.csv`)

| Source ID | QA Flag | Row Count | Explanation & Action Taken |
|---|---|---:|---|
| `PSI-101` | `added_from_workbook` | 1 | `Kapton 112` present in `Combined SAMER Results 06 02 14.xlsx` and 109-run final report but omitted from PSI summary CSV (`I-026`). |
| `PSI-101` | `secondary_aging_remeasurement` | 72 | Second aerosol measurement of parent smoke cloud after additional aging (`72` rows, `dup_of` set to parent `run_id`, `I-027`). |
| `PSI-102` | `outside_documented_hardware_range` | 2 | `PSI-102:TABLE_4` reports `10 cm/s`, above the `2–8 cm/s` hardware range stated in the SAME report (`I-028`). |
| `PSI-102` | `secondary_aging_remeasurement` | 34 | Second aerosol measurement of parent smoke cloud after additional aging (`34` rows, `dup_of` set to parent `run_id`, `I-027`). |
| `PSI-107` | `below_physical_range` | 8 | `Air Rate (cm/s)` is `-0.28` (5 rows) or `-5.92` (3 rows) from the negative intercept of the linear anemometer calibration $u_{a,0} = 0.94 \cdot \text{AIR} - 5.92$ at `AIR=6` and `AIR=0` (`I-016`). |
| `PSI-107` | `fuel_label_normalised` | 230 | `75 % Propylene` and `50 % Propylene` spacing/case normalised to `75% propylene` and `50% propylene` (`I-015`). |
| `PSI-25` | `date_year_typo_in_source` | 5 | Tests `O20–O22` (`2/26/2016`, `GMT=57`) and `T9`, `T18` (`6/24/2018`, `GMT=175`) have year typos in the raw table (`I-024`). Raw dates preserved without silent editing. |
| `PSI-25` | `fuel_label_normalised` | 129 | Raw geometry/material descriptions (e.g. `1/4" black rod`, `100 micron PMMA film 2 cm wide`) mapped to confirmed material (`PMMA`, `SIBAL`, `Nomex`, `wax candle`) per *BASS-II data FAQ.docx* (`I-019`); full text kept in `fuel_detail`. |
| `PSI-25` | `negative_gas_reading` | 13 | `Initial CO (ppm)` recorded as `-1` (sensor zero-offset artifact, `I-010`). Numeric value blanked with `invalid_value`; `-1` preserved in `value_text`. |
| `PSI-69` | `gas_sum_off` | 6 | Initial O2 + N2 + CO2 + He mole fractions sum to 0.98 due to source rounding (`I-022`). Values kept unchanged. |
| `PSI-69` | `identifier_reused` | 2 | FLEX Test #183 and #184 share `FLEX Identifier = 193F001`. Keyed by `FLEX Test #`, so `run_id` stays unique. |
| `PSI-69` | `impossible_value_nulled` | 1 | FLEX Test #114 (`C11M201`) recorded `0 mmHg` ambient pressure (`I-020`). `pressure_kpa` blanked to NULL + `invalid_value`; raw `0` kept in `pressure_raw`. |
| `PSI-98` | `dimensions_swapped_in_source` | 2 | Raw CSV swapped sample length (`40.6 cm`) and width (`94 cm`); corrected to `940 mm x 406 mm` (`I-030`). |
| `PSI-98` | `suspect_thickness_unit` | 2 | Raw CSV reports `0.37 cm` (`3.7 mm`) thickness for thin SIBAL fabric (likely `0.37 mm`, `I-031`). |

---

## 4. Open Science Decisions for Malak (9 Open of 31 Logged Issues)

Full log in `docs/ISSUES_LOG.csv` (and `processed/issues.csv`):

| Issue ID | Source | Column | Severity | Decision Needed / Status |
|---|---|---|---|---|
| `I-001` | `PSI-69` | `Burning rate; mm` | `high` | Keep value_num = NULL + unavailable_in_source in run_measurements.csv per strict contract rule (raw text preserved in value_text); document mm^2/s evidence in Data Dictionary for Malak. |
| `I-006` | `PSI-25` | `Fan display / Air display` | `high` | flow_cm_s stays NULL + pending_review (for single numeric air display rows) or not_parseable (for multi-step text) until Malak approves applying U = 1.0066 * Air display. |
| `I-007` | `PSI-25` | `(calibration)` | `info` | Recorded as a cross-experiment dependency in Data Dictionary and Provenance Map; awaits Malak sign-off before populating flow_cm_s. |
| `I-008` | `PSI-25` | `Calibrated initial/final O2 % by vol` | `medium` | Both stored (o2_vol_pct uses initial with o2_basis='initial'; o2_final_vol_pct in run_measurements.csv). Malak confirms ranking basis. |
| `I-016` | `PSI-107` | `Air Rate (cm/s)` | `medium` | Kept as-is in flow_cm_s and flagged below_physical_range so Malak can decide whether to clamp negative calibration-intercept values to 0 cm/s. |
| `I-024` | `PSI-25` | `Date` | `low` | Kept raw date in test_date/test_date_raw without silent correction; flagged date_year_typo_in_source. |
| `I-025` | `PSI-107` | `Dotson_umd_0117N_10980.pdf` | `info` | Documented in Data Dictionary and Coverage Matrix notes; not mixed into flight CSV parser unless requested. |
| `I-028` | `PSI-102` | `Air Flow (cm/s) on Sample 4` | `medium` | Kept as reported (10 cm/s) and flagged outside_documented_hardware_range for Malak. |
| `I-031` | `PSI-98` | `Sample Thickness (cm)` | `low` | Kept as 3.7 mm in run_measurements.csv and flagged suspect_thickness_unit; Malak should not use thickness in ranking. |

*(The remaining 22 issues in `ISSUES_LOG.csv` were resolved during Stage 2 and Stage 3 document verification.)*
