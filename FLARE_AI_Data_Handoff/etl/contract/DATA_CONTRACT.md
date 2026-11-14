# FLARE AI — Data Contract (v0.3)

**Owners:** Data Engineering (Farah El Qady — `PSI-69`, `PSI-25`, `PSI-107`; Salma — `PSI-98`, `PSI-101`, `PSI-102`)  
**Status:** Release Candidate (`v0.3`). Ready for sign-off from Zeiad (Backend/DB), Malak (Science), Karim (AI/RAG), and Farah Khafagy (Frontend/UI).  
**Golden Rule:** If the code and this document disagree, the code is wrong.

---

## 1. What this contract is

This is the promise Data Engineering makes to the rest of the team: *"Every file we hand you will look exactly like this."*
Zeiad builds his database tables and API endpoints from it, Malak builds the physics ranking on it, Karim builds RAG retrieval on it, and Farah Khafagy builds the UI cards and badges from it. Any change to a column name, type, or enum requires bumping the contract version and logging it in Section 12.

We hand over five files in `processed/` (production) and `fixtures/` (lightweight test samples):

| Output | What it is | Who uses it |
|---|---|---|
| `runs.csv` | One row per experiment run (`29` core columns shared across all 6 investigations) | Zeiad (DB/API), Malak (ranking), Farah Khafagy (explorer table) |
| `run_measurements.csv` | Every experiment-specific value per run in "long" format (`run_id`, `variable`, `value_num`, `value_text`, `unit`, `missing_reason`, `source_column`) | Zeiad (detail view / charts), Malak (domain metrics) |
| `corpus_chunks.jsonl` | NASA document text cut into `~800–1,200` char chunks with `~150` char overlap, SHA-256, DOI, and page citations | Karim (RAG retrieval), Farah Khafagy (citation drawer) |
| `coverage.csv` | Parameter coverage & explicit research-gap matrix (`COV-*` and `GAP-*` cells) | Malak (gap analysis), Farah Khafagy (heatmap/gap view) |
| `issues.csv` | Machine-readable log of every data anomaly, portal conflict, and science decision | Malak (science review), Zeiad & Farah Khafagy (QA transparency) |

---

## 2. Ground rules (non-negotiable)

1. **Raw is read-only.** Files in `data/raw/` are never edited. `verify_raw.ps1` / `verify_raw()` must pass before any ETL run.
2. **Never guess.** If a unit, definition, or value isn't stated in a NASA source, the canonical field is `NULL` (`""` in CSV) and gets an explicit `missing_reason`.
3. **Never fill gaps.** No imputing, no zero-fill, no forward-fill, no copying across rows (e.g. `PSI-102` rows saying *"same conditions as 1–4"* stay `NULL` with `not_reported`).
4. **Every number has a trail.** Every row points back to its raw file, the file's SHA-256, and the 1-based row number.
5. **Gravity is per row**, not per investigation (`PSI-101` and `PSI-102` contain both ISS `microgravity` rows and `normal_gravity` ground baseline rows; `PSI-102` CSV table rows with unstated gravity use `unknown`).
6. **`partial_gravity` needs evidence.** Any row labelled `partial_gravity` must carry a non-null `gravity_evidence_id`. Without it the row is **rejected**.
7. **Flag, don't delete.** Duplicates, secondary-aging re-measurements, and suspicious values are flagged in `qa_flags` and kept. Only hard-rule violations (Section 7) or confirmed phantom rows go to `rejected.csv` with an explicit reason.

---

## 3. Canonical units

| Quantity | Canonical field | Unit | Conversion from source |
|---|---|---|---|
| Oxygen | `o2_vol_pct` | `% by volume` (`0–100`) | **FLEX (`PSI-69`):** mole fraction $\times 100$ (ideal-gas mole fraction = volume fraction). **BASS-II (`PSI-25`):** `Calibrated initial O2 % by vol` as-is (`o2_basis = 'initial'`). **SAFFIRE-I (`PSI-98`):** midpoint of `21.5 - 21.7` (`21.6`, `o2_basis = 'range_midpoint'`) or `21.5` (`~ 21.5`), with raw string preserved. **SPICE (`PSI-107`), SAME-R (`PSI-101`), SAME (`PSI-102`):** `NULL` (`unavailable_in_source`). |
| Pressure | `pressure_kpa` | `kPa` | **FLEX (`PSI-69`):** `mmHg` $\times 0.133322$ (`pressure_raw` kept in `mmHg`). **All other 5 sources:** `NULL` (`unavailable_in_source`). |
| Flow | `flow_cm_s` | `cm/s` | **SPICE (`PSI-107`):** `Air Rate (cm/s)` as-is. **SAFFIRE-I (`PSI-98`):** `Air Flow (cm/s)` as-is (`20 cm/s`). **SAME-R (`PSI-101`) & SAME (`PSI-102`):** `Inlet velocity (cm/s)` / `Air Flow (cm/s)` as-is. **BASS-II (`PSI-25`):** `NULL` (`pending_review` on 25 single-number `Air display` rows awaiting Malak sign-off on $U = 1.0066 \times \text{Air display}$; `not_parseable` on 100 multi-step rows; `not_reported` on 4 blank rows). **FLEX (`PSI-69`):** `NULL` (`unavailable_in_source`). |

---

## 4. `runs.csv` — exact 36-column schema

Every row in `processed/runs.csv` and `fixtures/runs.csv` has these exact 36 columns (`RUN_FIELDS` in `etl/core/common.py`) in this exact order:

| # | Field | Type | Required | Allowed Values / Meaning |
|---:|---|---|---|---|
| 1 | `run_id` | text | ✅ | Stable unique primary key, format `{source_id}:{native_key}` (e.g. `PSI-69:FLEX-001`, `PSI-25:B1`, `PSI-107:D45-143708-R001`, `PSI-101:Kapton_51`, `PSI-102:FLIGHT_1`, `PSI-98:S1`). |
| 2 | `source_id` | enum | ✅ | `PSI-69` \| `PSI-25` \| `PSI-107` \| `PSI-98` \| `PSI-101` \| `PSI-102` |
| 3 | `investigation` | text | ✅ | `FLEX` \| `BASS-II` \| `SPICE` \| `SAFFIRE-I` \| `SAME-R` \| `SAME` |
| 4 | `native_test_id` | text | | Source's own test ID (`FLEX Test #`, `BASS-II Test #`, `SAME Test #`, `SAFFIRE Sample #`). `NULL` for SPICE. |
| 5 | `domain` | enum | ✅ | `liquid_droplet` \| `solid` \| `gas_jet` \| `smoke` *(Salma's `aerosol_smoke` maps to `smoke`)* |
| 6 | `platform` | enum | ✅ | `ISS` \| `Cygnus` \| `ground` \| `drop_tower` \| `aircraft` \| `unknown` |
| 7 | `gravity_regime` | enum | ✅ | `microgravity` \| `partial_gravity` \| `normal_gravity` \| `unknown` |
| 8 | `gravity_evidence_id` | text | if partial | Citation ID proving the partial-gravity level (required if `gravity_regime == 'partial_gravity'`). |
| 9 | `test_date` | date | | ISO `YYYY-MM-DD` when verified (`2009` for SPICE; `2016-06-14` for SAFFIRE-I). `NULL` if unknown. |
| 10 | `test_date_raw` | text | | Date exactly as written in the raw source (e.g. SPICE DOY `45`, BASS-II `2/26/2016`). |
| 11 | `test_time_gmt` | text | | `HH:MM:SS` normalised, or `NULL` if blank/`LOS`/`n/a`. |
| 12 | `fuel_raw` | text | ✅ | Fuel/material text exactly as written in the raw source. |
| 13 | `fuel` | text | ✅ | Normalised controlled-vocabulary material name (`heptane`, `methanol`, `PMMA`, `SIBAL`, `Nomex`, `wax candle`, `ethylene`, `methane`, `propane`, `propylene`, `75% propylene`, `50% propylene`, `Kapton`, `Teflon`, `Silicone`, `Pyrell`, `Cotton lamp wick`, `Dibutyl phthalate (DBP)`). |
| 14 | `fuel_detail` | text | | Sample geometry, dilution, or test description (`100 micron PMMA film 2 cm wide`, `Concurrent flow burn`, etc.). |
| 15 | `o2_vol_pct` | number | | Canonical oxygen volume % (`0–100`). |
| 16 | `o2_basis` | enum | | `initial` \| `final` \| `nominal` \| `range_midpoint` \| `approximate` |
| 17 | `o2_missing_reason` | enum | if NULL | Required whenever `o2_vol_pct` is `NULL`. |
| 18 | `o2_raw` | text | | Raw O₂ value before conversion (`mole fraction` in FLEX, `"21.5 - 21.7"` in SAFFIRE-I). |
| 19 | `o2_raw_unit` | text | | Raw O₂ unit (`mole_fraction`, `vol_pct`). |
| 20 | `pressure_kpa` | number | | Canonical ambient pressure in `kPa`. |
| 21 | `pressure_missing_reason` | enum | if NULL | Required whenever `pressure_kpa` is `NULL`. |
| 22 | `pressure_raw` | text | | Raw pressure string before unit conversion (`mmHg` in FLEX). |
| 23 | `pressure_raw_unit` | text | | Raw pressure unit (`mmHg`). |
| 24 | `flow_cm_s` | number | | Canonical airflow velocity in `cm/s`. |
| 25 | `flow_basis` | text | | Physical location/meaning of flow (`coflow_air_velocity`, `inlet`, `duct`). |
| 26 | `flow_missing_reason` | enum | if NULL | Required whenever `flow_cm_s` is `NULL`. |
| 27 | `flow_raw` | text | | Raw flow string before conversion/calibration (`Air display` in BASS-II). |
| 28 | `flow_raw_unit` | text | | Raw flow unit (`cm/s`, `air_display_setting`). |
| 29 | `outcome_raw` | text | | Raw test outcome string (FLEX `Test end`: `Extinguishment`, `Consumption`, etc.). |
| 30 | `dup_status` | enum | ✅ | `unique` \| `exact_duplicate` \| `near_duplicate` |
| 31 | `dup_of` | text | | `run_id` of the parent/original row (used for `exact_duplicate`, `near_duplicate`, and Salma's `parent_run_code` on secondary-aging `51a` rows). |
| 32 | `qa_flags` | text | | Semicolon-separated list of soft QA flags (see Section 7). |
| 33 | `source_file` | text | ✅ | Relative path under `data/raw/`. |
| 34 | `source_sha256` | text | ✅ | SHA-256 checksum matching `data/raw_manifest.csv`. |
| 35 | `source_row` | int | ✅ | 1-based row number in the source table. |
| 36 | `etl_version` | text | ✅ | Version of the ETL pipeline (`0.1.0`). |

---

## 5. `run_measurements.csv` — long-format schema (7 columns)

All experiment-specific columns (FLEX droplet diameters & burning rate; BASS-II burn duration, flame spread rate, CO/CO₂ ppm, fan display; SPICE nozzle diameter, fuel flow rate, flame length at smoke point; SAME/SAME-R `rt_r0`, `heater_temp_c_derived`, `amd_um`, `dam_um`, `hc_sigma_g`, `hc_dg_um`, `m0_per_cm3`, `m1_mm_per_cm3`, aging times; SAFFIRE-I `ignition_power_w`, `burn_time_s`, sample dimensions) are stored as rows in `run_measurements.csv`:

| Field | Type | Meaning |
|---|---|---|
| `run_id` | text | Foreign key to `runs.csv` (`0` orphan `run_id`s allowed). |
| `variable` | text | Canonical snake_case variable name (documented below and in `docs/DATA_DICTIONARY.md`). |
| `value_num` | number | Parsed float if unambiguous, else `NULL`. |
| `value_text` | text | Exact raw string from the source cell. |
| `unit` | text | Verified physical unit (`mm`, `mm^2/s`, `s`, `ppm`, `um`, `1/cm3`, etc.), or `NULL` if unverified. |
| `missing_reason` | enum | Required if `value_num` is `NULL`. |
| `source_column` | text | Exact column header in the raw file. |

### Complete Catalog of `variable` Names in `run_measurements.csv`

| Source(s) | `variable` | `unit` | Meaning |
|---|---|---|---|
| `PSI-69` (FLEX) | `flex_identifier` | *(text)* | NASA 7-character test point code (`20CAL08`, `C11M201`, etc.) |
| `PSI-69` (FLEX) | `n2_initial_mole_fraction` | `mole fraction` | Initial $\text{N}_2$ mole fraction (`0–0.86`) |
| `PSI-69` (FLEX) | `co_initial_mole_fraction` | `mole fraction` | Initial $\text{CO}_2$ diluent mole fraction (`0–0.70`, raw header `CO...`, `I-002`) |
| `PSI-69` (FLEX) | `he_initial_mole_fraction` | `mole fraction` | Initial $\text{He}$ diluent mole fraction (`0–0.50`) |
| `PSI-69` (FLEX) | `droplet_initial_diameter` | `mm` | Initial fuel droplet diameter $d_0$ (`1.12–5.39 mm`) |
| `PSI-69` (FLEX) | `flame_extinction_diameter` | `mm` | Droplet diameter at visible flame extinction $d_{\text{ext}}$ (`0.33–4.64 mm`) |
| `PSI-69` (FLEX) | `burning_rate` | *(NULL in CSV)* | $d^2$-law burning rate constant $K$ (`0.31–1.27 mm^2/s`, raw header `Burning rate; mm`, `I-001`) |
| `PSI-69` (FLEX) | `burn_time` | `s` | Total burn duration $t_{\text{burn}}$ (`0.43–51.5 s`) |
| `PSI-69` (FLEX) | `test_end` | *(text)* | Outcome (`Extinguishment`, `Consumption`, `LIH`, etc.) |
| `PSI-25` (BASS-II) | `sample_id`, `pi_name`, `igniter_location`, `lens_mm`, `f_stop`, `events`, `notes` | *(text)* | Experiment metadata, camera optics, and crew notes |
| `PSI-25` (BASS-II) | `fan_display`, `air_display` | *(setting)* | Raw MSG fan / air flow display string (`pending_review` or `not_parseable` in `runs.csv`, `I-006`) |
| `PSI-25` (BASS-II) | `o2_final_vol_pct` | `% by vol` | Final calibrated $\text{O}_2$ volume % after burn (`10.2–22.1%`, `I-008`) |
| `PSI-25` (BASS-II) | `co2_initial_ppm`, `co2_final_ppm`, `co_initial_ppm`, `co_final_ppm` | `ppm` | Initial and final $\text{CO}_2$ and $\text{CO}$ concentrations in `ppm` |
| `PSI-25` (BASS-II) | `burn_duration_s` | `s` | Burn duration (`1–489 s`) |
| `PSI-25` (BASS-II) | `flame_spread_rate_mm_s` | `mm/s` | Flame spread rate (`0.008–5.64 mm/s`) |
| `PSI-107` (SPICE) | `nozzle_diameter_mm` | `mm` | Burner nozzle inner diameter (`0.4, 0.8, 1.6 mm`) |
| `PSI-107` (SPICE) | `fuel_rate_mg_s`, `hc_fuel_rate_mg_s` | `mg/s` | Total gas mixture mass flow rate and hydrocarbon-only mass flow rate (`I-017`) |
| `PSI-107` (SPICE) | `flame_length_mm` | `mm` | Luminous flame length at the smoke point (`1.84–46.48 mm`) |
| `PSI-107` (SPICE) | `video_camera_id`, `stills_Sequence` | *(text)* | Camera and D2Xs still-image sequence identifiers |
| `PSI-101` / `PSI-102` | `rt_r0`, `heater_temp_c_derived` | `ratio`, `degC` | Heater resistance ratio ($R_t/R_0$) and derived pyrolysis temperature (°C) |
| `PSI-101` / `PSI-102` | `heating_duration_s`, `primary_aging_s`, `primary_mixing_s`, `net_aging_s`, `net_aging_s_workbook`, `aging_duration_s` | `s` | Smoke generation, mixing, and aging durations |
| `PSI-101` / `PSI-102` | `amd_um`, `dam_um`, `dam_dusttrak_a_um`, `dam_dusttrak_b_um`, `cmd_um`, `hc_dg_um` | `um` | Particle size diameters ($\text{AMD}$, $d_{\text{am}}$, DustTrak A/B, $\text{CMD}$, Hatch-Choate $d_g$) in $\mu\text{m}$ |
| `PSI-101` / `PSI-102` | `hc_sigma_g`, `m0_per_cm3`, `m1_mm_per_cm3`, `mass_loss_mg`, `weight_loss_rate_mg_min` | `unitless`, `1/cm3`, `mm/cm3`, `mg`, `mg/min` | Geometric standard deviation ($\sigma_g$), aerosol moments ($M_0, M_1$), and sample mass loss |
| `PSI-98` (SAFFIRE-I) | `flow_direction`, `o2_vol_pct_low`, `o2_vol_pct_high`, `ignition_power_w`, `ignition_time_s`, `burn_time_s`, `sample_length_mm`, `sample_width_mm`, `sample_thickness_mm` | *(text)*, `% vol`, `W`, `s`, `mm` | SAFFIRE-I flow direction (`concurrent`/`opposed`), $\text{O}_2$ bounds, igniter power/time, burn duration, and sample dimensions |

---

## 6. Allowed `missing_reason` values

Every `NULL` in `o2_vol_pct`, `pressure_kpa`, `flow_cm_s`, or `run_measurements.value_num` **must** carry one of these 5 codes:

| `missing_reason` | Meaning | Examples |
|---|---|---|
| `unavailable_in_source` | The source table has no column for this variable, or its unit is ambiguous in the raw header | SPICE, SAME, and SAME-R have no `o2_vol_pct` or `pressure_kpa` column; BASS-II and SAFFIRE-I CSVs have no `pressure_kpa` column; FLEX has no `flow_cm_s` column. |
| `not_reported` | The column exists in the source table, but this specific row's cell is blank or `"n/a"` | 25 SPICE rows with blank `Air Rate (cm/s)`; 4 BASS-II rows with blank `Air display`; 12 `PSI-102` rows with blank airflow (`8` ground secondary-aging rows + `4` `"same conditions as 1-4"` rows). |
| `invalid_value` | The cell contains an impossible physical value or telemetry loss code | FLEX Test 114 (`Ambient pressure = 0 mmHg`); BASS-II `Initial CO = -1 ppm`; SPICE `Ignition Time = LOS`. |
| `not_parseable` | The cell contains multi-step or free-text notes that cannot be reduced to a single scalar | 100 BASS-II `Fan display` / `Air display` rows with multi-step ramps (`"3.5 (68) 1.7 1.25..."`, `"14 to 5"`, `"off"`). |
| `pending_review` | A numeric value exists and a calibration formula was found, but awaits Malak's science sign-off | 25 BASS-II single-number `Air display` rows awaiting approval of $U = 1.0066 \times \text{Air display}$. |

---

## 7. Validation rules & `qa_flags` catalog

### Hard rules (violating rows are routed to `rejected.csv`):
- `run_id` missing or not unique
- `gravity_regime == 'partial_gravity'` without `gravity_evidence_id`
- `gravity_regime`, `domain`, or `platform` not in the allowed enums
- Any `NULL` canonical variable (`o2_vol_pct`, `pressure_kpa`, `flow_cm_s`) missing a valid `missing_reason`
- Any non-null canonical variable carrying a `missing_reason`
- `source_sha256` mismatch against `data/raw_manifest.csv`
- Confirmed phantom row in source CSV (`PSI-101` `Teflon, 57`, which is a copy-paste phantom of `Lampwick, 57`)

### Soft QA flags (`runs.qa_flags`, semicolon-delimited):

| `qa_flags` code | Investigation(s) | Meaning |
|---|---|---|
| `impossible_value_nulled` | `PSI-69` | Impossible `o2_vol_pct` outside `0–100` or `pressure_kpa <= 0` blanked to `NULL` + `invalid_value` (FLEX Test 114 `0 mmHg`). |
| `identifier_reused` | `PSI-69` | Two distinct runs share the same secondary identifier (`FLEX Test #183` & `#184` both have `193F001`). |
| `gas_sum_off` | `PSI-69` | Initial gas mole fractions (`O2 + N2 + CO2 + He`) sum to `0.98` (`>0.01` from `1.0`) due to source rounding. |
| `fuel_label_normalised` | All | `fuel` was mapped from a raw geometry/spacing string in `fuel_raw` to a controlled material name. |
| `negative_gas_reading` | `PSI-25` | `Initial CO (ppm)` recorded as `-1` (zero-offset artifact); numeric value nulled in `run_measurements.csv`. |
| `date_year_typo_in_source` | `PSI-25` | Source `Date` year (`2016` on `O20–O22`, `2018` on `T9, T18`) conflicts with `GMT` day-of-year and mission window (`2014`). |
| `below_physical_range` | `PSI-107` | `flow_cm_s < 0` (`-5.92` on 3 rows, `-0.28` on 5 rows) from negative intercept of linear anemometer calibration $u_{a,0} = 0.94 \cdot \text{AIR} - 5.92$. |
| `secondary_aging_remeasurement` | `PSI-101`, `PSI-102` | Row (e.g. `51a`, `61a`, `11a`) is a second aerosol measurement of the parent burn (`dup_of` points to parent `run_id`), not a new ignition. |
| `added_from_workbook` | `PSI-101` | Run (`Kapton 112`) is present in the master analyzed workbook and final report (`109` flight runs) but omitted from the PSI summary CSV. |
| `outside_documented_hardware_range` | `PSI-102` | `PSI-102_TABLE_4` reports `flow_cm_s = 10 cm/s`, above the `2–8 cm/s` hardware range stated in the SAME report. |
| `dimensions_swapped_in_source` | `PSI-98` | Raw CSV swapped sample length (`40.6 cm`) and width (`94 cm`) relative to the `0.94 m × 0.4 m` SAFFIRE-I hardware spec. |
| `suspect_thickness_unit` | `PSI-98` | Raw CSV reports `0.37 cm` (`3.7 mm`) thickness for thin SIBAL fabric (likely `0.37 mm`). |

---

## 8. Reconciliation of Salma's `Preprocessing` Outputs (`PSI-98`, `PSI-101`, `PSI-102`)

To merge Salma's `PSI-101_runs.csv` (`169` rows), `PSI-102_runs.csv` (`114` rows), and `PSI-98_runs.csv` (`2` rows) with Farah's `PSI-69` (`274` rows), `PSI-25` (`129` rows), and `PSI-107` (`469` rows) without schema clashes:

1. **Column renaming (`Salma` $\rightarrow$ `Contract v0.3`):**
   - `investigation_id` $\rightarrow$ `source_id`
   - `run_code` $\rightarrow$ `run_id` (normalised to `{source_id}:{key}`)
   - `source_test_id` $\rightarrow$ `native_test_id`
   - `material` $\rightarrow$ `fuel` (and raw string in `fuel_raw`, `description` in `fuel_detail`)
   - `domain = 'aerosol_smoke'` $\rightarrow$ `domain = 'smoke'`
   - `platform`: `"International Space Station (ISS)"` $\rightarrow$ `ISS`; `"ground (NASA GRC)"` $\rightarrow$ `ground`; `"Cygnus cargo vehicle..."` $\rightarrow$ `Cygnus`
   - `flow_definition` $\rightarrow$ `flow_basis`
   - `parent_run_code` $\rightarrow$ `dup_of` (and `is_secondary_aging == True` adds `secondary_aging_remeasurement` to `qa_flags`)
2. **Missing-reason alignment:**
   - In `PSI-101` and `PSI-102`, `o2_missing_reason` and `pressure_missing_reason` become `unavailable_in_source` (since neither table has an O₂ or pressure column).
   - On the `12` `PSI-102` rows where `flow_cm_s` is `NULL`, `flow_missing_reason` is set to `not_reported`.
3. **Wide-to-Long measurement pivot:**
   - Salma's 27 aerosol and SAFFIRE columns (`rt_r0`, `heater_temp_c_derived`, `heating_duration_s`, `primary_aging_s`, `primary_mixing_s`, `net_aging_s`, `net_aging_s_workbook`, `aging_duration_s`, `ignition_power_w`, `ignition_time_s`, `burn_time_s`, `sample_thickness_mm`, `sample_length_mm`, `sample_width_mm`, `weight_loss_rate_mg_min`, `mass_loss_mg`, `amd_um`, `dam_um`, `dam_dusttrak_a_um`, `dam_dusttrak_b_um`, `cmd_um`, `hc_sigma_g`, `hc_dg_um`, `m0_per_cm3`, `m1_mm_per_cm3`) pivot cleanly into `run_measurements.csv`.

---

## 9. `corpus_chunks.jsonl` — text for the chatbot

One JSON object per line:

| Field | Meaning |
|---|---|
| `chunk_id` | `{source_id}:{doc_slug}:p{page}:c{n}`, deterministic |
| `source_id` | `PSI-69`, `PSI-25`, `PSI-107`, `PSI-98`, `PSI-101`, `PSI-102` |
| `doc_title` | Clean human-readable document title |
| `doc_file` | Relative path under `data/raw/` |
| `doc_sha256` | SHA-256 from `data/raw_manifest.csv` |
| `page_start`, `page_end` | PDF page or PPTX slide numbers (`null` for unpaginated `.docx`/`.doc`/`.txt`) |
| `section` | Detected section heading or slide title (`null` if none) |
| `text` | Chunk text (`~800–1,200` chars with `~150` char overlap, whitespace normalized) |
| `char_count` | Character count (`len(text)`) |
| `license` | `CC0-1.0` |
| `doi` | Investigation DOI from `data/source_registry.csv` |

---

## 9B. Supporting Tables (`coverage.csv`, `issues.csv`, `rejected.csv`, `_meta.json`)

### 1. `coverage.csv` (12 columns)
| Field | Meaning |
|---|---|
| `cell_id` | `COV-01`..`COV-24` for populated parameter cells; `GAP-25`..`GAP-33` for 0-run research/instrumentation gaps |
| `gravity_regime` | `microgravity` \| `normal_gravity` \| `partial_gravity` \| `unknown` |
| `domain` | `liquid_droplet` \| `solid` \| `gas_jet` \| `smoke` |
| `o2_band` | `low_o2 (<19%)` \| `normoxic_o2 (19-23%)` \| `enriched_o2 (>23%)` \| `unmeasured_o2` |
| `pressure_band` | `sub_atm (<85 kPa / ~0.7 atm)` \| `near_atm (85-115 kPa / ~1 atm)` \| `elevated_pressure (>115 kPa / 2-3 atm)` \| `unmeasured_pressure` |
| `flow_band` | `zero_or_negative_cal (<=0 cm/s)` \| `low_flow (0-15 cm/s)` \| `moderate_flow (15-40 cm/s)` \| `high_flow (>40 cm/s)` \| `pending_calibration (raw setting only)` \| `unmeasured_or_quiescent` |
| `total_runs` | Total parsed runs in this cell |
| `unique_runs` | Deduplicated runs (`dup_status == 'unique'`) in this cell |
| `sources` | Semicolon-separated `source_id`s covering this cell |
| `fuels` | Semicolon-separated normalised `fuel`s in this cell |
| `coverage_status` | `covered` ($\ge 5$ unique runs) \| `sparse (<5 unique runs)` \| `gap (0 runs)` |
| `gap_note` | Explanation of coverage or why the gap exists |

### 2. `issues.csv` (7 columns)
`issue_id`, `source_id`, `column`, `severity` (`high` \| `medium` \| `low` \| `info`), `status` (`open` \| `resolved`), `description`, `decision`.

### 3. `rejected.csv` (4 columns)
`run_id`, `source_id`, `source_row`, `reasons` (`0` rows in `v0.3`).

### 4. `_meta.json`
Contains `contract_version`, `etl_version`, `generated_utc`, `runs`, `measurements`, `rejected`, `corpus` summary, `fixtures` summary, and per-source breakdown (`by_source`).

---

## 10. Downstream Consumption Rules (Who Needs to Know What)

### For Zeiad (Backend / Database / API):
1. **Single unified schema:** Load `processed/runs.csv` (`36` columns) as the parent `runs` table (`PRIMARY KEY (run_id)`) and `processed/run_measurements.csv` (`7` columns) as the child `run_measurements` table (`FOREIGN KEY (run_id) REFERENCES runs(run_id)`).
2. **Default deduplication filter:** In summary counts and default search results, filter `dup_status = 'unique'` AND exclude `qa_flags LIKE '%secondary_aging_remeasurement%'` when counting independent burns (expose a toggle in the API so users can inspect duplicates and secondary-aging rows on demand).
3. **Never convert `NULL` to `0`:** `flow_cm_s = 0.0` is a real quiescent test (`0 cm/s`); `flow_cm_s = NULL` (`""` in CSV) means unknown/unreported and must return `null` in JSON alongside `flow_missing_reason`.

### For Malak (Science / Physics Ranking):
1. **Nine open science items across all 6 investigations (6 on Farah's 3 datasets + 3 on Salma's 3 datasets):**
   - **Farah's 3 datasets (`PSI-69`, `PSI-25`, `PSI-107`):**
     1. `I-001` (`PSI-69`): Confirm using `Burning rate; mm` as $K$ in $\text{mm}^2/\text{s}$ (proven by EIRD v4 p. 20 & $d^2$-law check).
     2. `I-006` / `I-007` (`PSI-25`): Confirm applying $U\text{ (cm/s)} = 1.0066 \times \text{Air display}$ to the 25 single-number `Air display` rows.
     3. `I-008` (`PSI-25`): Confirm `o2_basis = 'initial'` (`Calibrated initial O2 % by vol`) as the canonical O₂ ranking input.
     4. `I-016` (`PSI-107`): Decide whether to clamp the 8 negative anemometer calibration-intercept values (`-5.92` and `-0.28 cm/s`) to `0.0 cm/s` in the physics model or keep as-is.
     5. `I-024` (`PSI-25`): Note the 5 rows with year typos (`2016`/`2018` vs `2014` DOY).
     6. `I-025` (`PSI-107`): Decide whether the 36 normal-gravity (`1g`) SPICE smoke-point rows in Dotson's thesis Tables 6.3–6.4 should be digitized as a separate baseline table.
   - **Salma's 3 datasets (`PSI-98`, `PSI-101`, `PSI-102`):**
     7. `I-026` (`PSI-101` `Teflon 57` & `Kapton 112`): Confirm excluding phantom `Teflon 57` (duplicate of `Lampwick 57`) and keeping `Kapton 112` from the master workbook (`109` flight runs total).
     8. `I-031` (`PSI-98` `Sample Thickness = 0.37 cm`): Confirm keeping `sample_thickness_mm` flagged (`suspect_thickness_unit`) and excluded from ranking equations.
     9. `I-028` (`PSI-102` `Sample 4 Air Flow = 10 cm/s`): Confirm whether to keep `10 cm/s` flagged (`outside_documented_hardware_range`) or exclude `PSI-102:TABLE_*` summary rows in favor of the `64` flight + `42` ground workbook rows.

### For Karim (AI / RAG Chatbot):
1. **Index `processed/corpus_chunks.jsonl` (`1,312` chunks)** and preserve every metadata field (`chunk_id`, `source_id`, `doc_title`, `doc_file`, `doc_sha256`, `page_start`, `page_end`, `section`, `doi`, `license`).
2. **Ground every answer with `[chunk_id]` + `doc_title` + `page_start`–`page_end` + `doi`**, and use `processed/coverage.csv` (`GAP-*` rows) when the user asks about untested regimes (such as Lunar/Martian partial gravity).

### For Farah Khafagy (Frontend / UI):
1. **Render `missing_reason` badges whenever `o2_vol_pct`, `pressure_kpa`, or `flow_cm_s` is `null`:** show human-readable tooltips for `unavailable_in_source` (*"Not measured in this NASA investigation"*), `pending_review` (*"Raw setting recorded; calibration pending science sign-off"*), `not_parseable` (*"Multi-step ramp; see raw text"*), `invalid_value` (*"Sensor error nulled"*), and `not_reported` (*"Blank in NASA table"*).
2. **Render `qa_flags` pills and `dup_status` badges** (`unique`, `exact_duplicate`, `near_duplicate`, `secondary_aging_remeasurement`), and use `processed/coverage.csv` to power the Coverage vs. Research-Gap matrix view.

---

## 11. Change log

| Version | Date | Change |
|---|---|---|
| `v0.1` | 2026-11-14 | First draft |
| `v0.2` | 2026-11-14 | Impossible O₂/pressure values are blanked and flagged (`impossible_value_nulled`) instead of rejecting the whole row (FLEX test 114, `0 mmHg`). Added flags `identifier_reused`, `negative_gas_reading`, `date_year_typo_in_source`. |
| `v0.3` | 2026-11-14 | Added reconciliation rules and flags for Salma's three investigations (`PSI-98` SAFFIRE-I, `PSI-101` SAME-R, `PSI-102` SAME), added `unknown` to `gravity_regime` and `platform` enums, added `range_midpoint`/`approximate` to `o2_basis`, and added Section 10 downstream consumption rules for Zeiad and Malak. |
