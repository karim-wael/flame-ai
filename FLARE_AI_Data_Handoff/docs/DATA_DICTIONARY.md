# FLARE AI — Data Dictionary

**Owner:** Data Engineering (Farah El Qady, Salma)  
**Contract Version:** v0.3  
**ETL Version:** 0.1.0  

This document defines every column in the clean tables (`processed/runs.csv` and `processed/run_measurements.csv`), every variable name, its unit, and the exact NASA document in `data/raw/` that verifies its definition.

---

## 1. Canonical Runs Table (`processed/runs.csv`)

One row per experiment run across all 6 NASA PSI investigations (`1,157` rows total: `274` FLEX + `129` BASS-II + `469` SPICE + `169` SAME-R + `114` SAME + `2` SAFFIRE-I).

| Column | Type | Unit / Allowed Values | Meaning & Source Rule |
|---|---|---|---|
| `run_id` | string | `<source_id>:<key>` | Globally unique run identifier (e.g. `PSI-69:FLEX-001`, `PSI-25:B1`, `PSI-107:D45-143708-R001`, `PSI-101:Kapton_51`, `PSI-102:FLIGHT_1`, `PSI-98:S1`). Never null. |
| `source_id` | string | `PSI-69`, `PSI-25`, `PSI-107`, `PSI-101`, `PSI-102`, `PSI-98` | NASA Physical Sciences Informatics (PSI) study identifier. |
| `investigation` | string | `FLEX`, `BASS-II`, `SPICE`, `SAME-R`, `SAME`, `SAFFIRE-I` | Short NASA experiment name. |
| `native_test_id` | string | Free text or empty | Original test identifier in the raw CSV (`FLEX Test #` for PSI-69, `Test #` for PSI-25, empty for PSI-107 which has no native ID column). |
| `domain` | enum | `liquid_droplet`, `solid`, `gas_jet`, `smoke` | Physical combustion domain (`liquid_droplet` for FLEX, `solid` for BASS-II, `gas_jet` for SPICE). |
| `platform` | enum | `ISS`, `Cygnus`, `ground`, `drop_tower`, `aircraft` | Experimental facility platform (`ISS` for all 872 rows in the three flight CSVs). |
| `gravity_regime` | enum | `microgravity`, `partial_gravity`, `normal_gravity` | Gravity level per row (`microgravity` for all 872 ISS rows). |
| `gravity_evidence_id` | string | Citation ID or empty | Required whenever `gravity_regime = partial_gravity`; otherwise empty. |
| `test_date` | string | `YYYY-MM-DD` or empty | ISO-8601 test date. Converted from `Test Date` (FLEX), `Date` (BASS-II), and `2009` + `GMT date` day-of-year (SPICE, confirmed by *SPICE Final Report* p. 13: Feb 14 – Jun 23, 2009). |
| `test_date_raw` | string | Raw text | Exact string from the raw date/day column (`3/5/2009`, `2/19/2014`, `45`). |
| `test_time_gmt` | string | `HH:MM:SS`, `HH:MM`, or empty | Normalized GMT ignition/test time. Seconds are never invented if the source only gave `HH:MM` (e.g. `17:44`). |
| `fuel_raw` | string | Raw text | Exact string from the raw fuel column (`Methanol`, `1/4" black rod`, `75 % Propylene`). |
| `fuel` | string | Normalized text | Cleaned fuel label: `methanol`, `heptane` (FLEX); `PMMA`, `SIBAL`, `Nomex`, `wax candle` (BASS-II, confirmed via *BASS-II data FAQ.docx*); `ethylene`, `propane`, `propylene`, `75% propylene`, `50% propylene`, `methane` (SPICE). |
| `fuel_detail` | string | Text or empty | Sample geometry/color/igniter details preserved from `Fuel Sample Material` in BASS-II (e.g. `100 micron PMMA film 2 cm wide`, `1/4" black rod`). |
| `o2_vol_pct` | float | `% by volume` (`0–100`) or empty | Canonical ambient oxygen concentration. For ideal gases, volume % = mole fraction × 100. |
| `o2_basis` | string | `initial` or empty | Whether `o2_vol_pct` is the pre-ignition initial concentration (`initial` for both FLEX and BASS-II). |
| `o2_missing_reason` | enum | One of 5 allowed reasons or empty | Empty when `o2_vol_pct` is present; `unavailable_in_source` for all 469 SPICE rows. |
| `o2_raw` | string | Raw text | Exact cell text from the raw oxygen column. |
| `o2_raw_unit` | string | `mole fraction`, `% by vol`, or empty | Original unit in the raw table (`mole fraction` in FLEX, `% by vol` in BASS-II). |
| `pressure_kpa` | float | `kPa` (`> 0`) or empty | Canonical ambient pressure in kilopascals ($\text{kPa} = \text{mmHg} \times 0.133322$). Present for 273 of 274 FLEX rows (`70.17–309.29 kPa`). |
| `pressure_missing_reason` | enum | One of 5 allowed reasons or empty | `invalid_value` for FLEX Test 114 (`0 mmHg`, `I-020`); `unavailable_in_source` for BASS-II and SPICE. |
| `pressure_raw` | string | Raw text | Exact cell text from the raw pressure column (`757.7`, `0`). |
| `pressure_raw_unit` | string | `mmHg` or empty | Original pressure unit in the raw table (`mmHg` in FLEX). |
| `flow_cm_s` | float | `cm/s` or empty | Canonical oxidizer/air flow speed in cm/s. Present for 444 of 469 SPICE rows (`-5.92` to `85.28 cm/s`). |
| `flow_basis` | string | Description or empty | Physical meaning of the flow (`co-flow air velocity` for SPICE; `tunnel air velocity (from instrument display)` for BASS-II). |
| `flow_missing_reason` | enum | One of 5 allowed reasons or empty | `unavailable_in_source` for FLEX (quiescent chamber); `pending_review` or `not_parseable` for BASS-II (awaiting Malak approval of fan calibration); `not_reported` for 25 blank SPICE rows. |
| `flow_raw` | string | Raw text | Exact cell text from the raw flow column (`Air display` in BASS-II, `Air Rate (cm/s)` in SPICE). |
| `flow_raw_unit` | string | `cm/s`, `air display (instrument units)`, or empty | Original unit in the raw table. |
| `outcome_raw` | string | `Disruption`, `Extinction`, `Completion`, or empty | Test end outcome reported in FLEX (`Test end` column). Empty for BASS-II and SPICE. |
| `dup_status` | enum | `unique`, `exact_duplicate`, `near_duplicate` | Duplicate classification within each source (`815` unique, `34` exact duplicates in SPICE, `23` near duplicates in SPICE). |
| `dup_of` | string | `run_id` or empty | If `dup_status != unique`, points to the `run_id` of the first occurrence in the table. |
| `qa_flags` | string | Semicolon-separated flags | Soft quality flags on the row (see Section 3 below). |
| `source_file` | string | Relative path | Path under project root (e.g. `data/raw/PSI-69_FLEX/PSI-69_Experimental table_FLEX.csv`). |
| `source_sha256` | string | 64-char hex | SHA-256 checksum of `source_file`, verified against `data/raw_manifest.csv`. |
| `source_row` | integer | `1..N` | 1-based data row index in the raw CSV (excluding the header line). |
| `etl_version` | string | `0.1.0` | Version of the ETL pipeline that produced the row. |

---

## 2. Long-Format Measurements Table (`processed/run_measurements.csv`)

Every source-specific column is stored as one row per `(run_id, variable)` (`7,426` rows total).

| Column | Type | Meaning |
|---|---|---|
| `run_id` | string | Foreign key to `runs.csv`. |
| `variable` | string | Standardized snake_case measurement name (listed by source below). |
| `value_num` | float or empty | Parsed numeric value when the measurement is numeric and valid; empty if text-only, blank, unparseable, or unit-unconfirmed. |
| `value_text` | string | Exact cleaned string from the raw cell (always preserved, even when `value_num` is empty). |
| `unit` | string | Unit of `value_num` (empty when text-only or unit is unconfirmed in the raw header). |
| `missing_reason` | enum or empty | Why `value_num` is empty (`unavailable_in_source`, `not_reported`, `invalid_value`, `not_parseable`). |
| `source_column` | string | Exact column header in the raw NASA CSV. |

### 2.1 PSI-69 (FLEX) Variables in `run_measurements.csv`

| `variable` | `source_column` | `unit` | Document-Verified Definition |
|---|---|---|---|
| `flex_identifier` | `FLEX Identifier` | *(text)* | NASA GRC test point code (e.g. `20CAL08`, `C11M201`), matching the per-test `.txt` filenames in `data/raw/PSI-69_FLEX/`. |
| `n2_initial_mole_fraction` | `N initial ambient composition; mole fraction` | `mole fraction` | Initial ambient nitrogen ($\text{N}_2$) mole fraction (`0.09–0.86`). Subscript `2` was stripped in the CSV header (*FLEX_EIRD_v4.pdf* §5.1.5, p. 38). |
| `co_initial_mole_fraction` | `CO initial ambient composition; mole fraction` | `mole fraction` | **Physical species is carbon dioxide ($\text{CO}_2$) suppressant/diluent** (`0–0.70` mole fraction). Confirmed by *FLEX_EIRD_v4.pdf* §5.1.4 (p. 38) and *FLEX_Test_Plan.pdf* Tables 8, 11, 12 (pp. 8, 14, 15). Subscript `2` was stripped in the CSV header just like `O` ($\text{O}_2$) and `N` ($\text{N}_2$). (`I-002`) |
| `he_initial_mole_fraction` | `He initial ambient composition; mole fraction` | `mole fraction` | Initial ambient helium ($\text{He}$) suppressant/diluent mole fraction (`0–0.45`, *FLEX_Test_Plan.pdf* Table 9, p. 10). |
| `droplet_initial_diameter` | `Droplet initial diameter; mm` | `mm` | Deployed fuel droplet diameter $d_0$ prior to ignition (`1.12–5.33 mm`, 12 rows not reported). |
| `flame_extinction_diameter` | `Visible flame extinction diameter; mm` | `mm` | Droplet diameter $d_{\text{ext}}$ at visible flame extinction (`0.61–3.96 mm`, 77 rows blank, mostly `Disruption` runs). |
| `burning_rate_raw` | `Burning rate; mm` | *(empty — `unavailable_in_source`)* | Raw header says `Burning rate; mm` (missing time/exponent). *FLEX_EIRD_v4.pdf* p. 20 & Table 13 (p. 76) define the quasi-steady droplet burning rate constant $K = -d(d^2)/dt$ in **$\text{mm}^2/\text{s}$** ($d^2$-law, matching $(d_0^2 - d_{\text{ext}}^2)/t_{\text{burn}}$ across the table). Per strict contract rule, `value_num` is left empty (`unavailable_in_source`) and raw numbers (`0.05–1.06`) are preserved in `value_text` (`I-001`). |
| `burn_time` | `Burn time; s` | `s` | Total visible burn duration (`0.7–46.22 s`). Two approximate values (`~6`, `~9`) have `value_num` empty + `not_parseable` (`I-023`). |

### 2.2 PSI-25 (BASS-II) Variables in `run_measurements.csv`

Verified against *BASS-II data FAQ.docx* and *Fan calibration data.xlsx* in `data/raw/PSI-25_BASS-II/`:

| `variable` | `source_column` | `unit` | Document-Verified Definition |
|---|---|---|---|
| `principal_investigator` | `PI` | *(text)* | Lead investigator (`Bhattacharjee`, `Ferkul`, `Fernandez-Pello`, `Miller`, `Olson`, `T'ien`). |
| `gmt_day_of_year` | `GMT` | `day of year` | Day of year in 2014 (`45–216`, corresponding to Feb 14 – Aug 4, 2014; *BASS-II data FAQ.docx*). |
| `sample_number` | `Sample #` | `1` *(text if suffix)* | Sample card/rod identifier (`128–244`, often with `m`/`M`/`L` suffix; alphanumeric codes keep `value_text` with `not_parseable`). |
| `flow_restrictor_count` | `Flow restrictor` | `1` | Number of perforated restrictor plates on the inlet screen: `0` = highest flow / lowest restriction, `1` = medium, `2` = lowest flow / highest restriction (*BASS-II data FAQ.docx*). |
| `fan_display` | `Fan display` | *(text)* | Instantaneous fan voltage $\times 10$ on the video display (max `122` = `12.2 V`, fan turns off near `38` = `3.8 V`), or control-box potentiometer settings (`pot`, max `10`) (*BASS-II data FAQ.docx*, *Fan calibration data.xlsx*). |
| `air_display` | `Air display` | *(text)* | Duct flow readout on the video display (`~1 min` response time). Related to centerline velocity via $U\text{ (cm/s)} = 1.0066 \times \text{Air display}$ (*Fan calibration data.xlsx*, based on SPICE fan calibration at 56 mm downstream). |
| `radiometer_gain` | `Radiometer gain   (1000   250   50   10)` | `1` | Uncalibrated radiometer gain setting (`10`, `50`, `250`, `1000`) adjusted to avoid saturation (*BASS-II data FAQ.docx*). |
| `total_frames_shot` | `Total Frames Shot` | `1` | Count of Nikon digital still frames taken (`0–369`; text entries like `none`, `video`, `300+ +102` kept in `value_text`). |
| `o2_final_vol_pct` | `Calibrated final O2 % by vol` | `% by vol` | Post-burn calibrated $\text{O}_2$ concentration (`0.6–40.4%`; offset-calibrated against ISS MCA cabin air reading, *BASS-II data FAQ.docx*). |
| `co2_initial_vol_pct` | `Initial CO2 % by vol` | `% by vol` | Pre-burn $\text{CO}_2$ reading from the CDM sensor (`0.19–0.73%`). |
| `co2_final_vol_pct` | `Final CO2 % by vol` | `% by vol` | Post-burn $\text{CO}_2$ reading from the CDM sensor (`0.20–0.85%`). |
| `co_initial_ppm` | `Initial CO (ppm)` | `ppm` | Pre-burn $\text{CO}$ reading from the CSA-CP sensor. `-1` sensor zero-offset artifacts (`13` rows) and `OR` (`>1000 ppm` over-range) are nulled with `invalid_value` (`I-010`). |
| `co_final_ppm` | `Final CO (ppm)` | `ppm` | Post-burn $\text{CO}$ reading from the CSA-CP sensor (`0–423 ppm`; `OR`/`over` nulled with `invalid_value`, `>500` nulled with `not_parseable`). |

### 2.3 PSI-107 (SPICE) Variables in `run_measurements.csv`

Verified against *SPICE Final Report 12_2_2012.pdf*, *SPICE RPT-002 Science Verif Report_May 2007.pdf*, and *Dotson_umd_0117N_10980.pdf*:

| `variable` | `source_column` | `unit` | Document-Verified Definition |
|---|---|---|---|
| `gmt_day_of_year` | `GMT date` | `day of year` | ISS flight day of year in **2009** (`45, 48, 52, 55, 58, 119, 136, 167, 168, 173, 174` = Feb 14 – Jun 23, 2009; *SPICE Final Report* p. 13). |
| `gmt_ignition_raw` | `GMT ignition` | *(text)* | Raw ignition timestamp or telemetry status (`LOS` = loss of signal, `Ku LOS`, `no ku`, `n/a`). |
| `gmt_flame_off_raw` | `GMT  Flame Off ` | *(text)* | Raw flame-out timestamp or telemetry status (note double space and trailing space in raw header). |
| `nozzle_diameter` | `Nozzle (mm)` | `mm` | Inner diameter of the interchangeable burner tube (`0.4064`, `0.762`, or `1.6002 mm`; *SPICE RPT-002* p. A-7, *Dotson thesis* p. 22). |
| `fuel_rate_sccm` | `Fuel Rate (sccm)` | `sccm` | Volumetric fuel flow rate in standard $\text{cm}^3/\text{min}$ corrected from the Sierra mass flow controller $\text{N}_2$-equivalent reading using gas K-factors (*Dotson thesis* §3.1.2, Table 3.2, p. 28). |
| `fuel_rate_mg_s` | `Fuel Rate (mg/s)` | `mg/s` | Total mass flow rate of the fuel stream (including $\text{N}_2$ diluent for the 50% and 75% propylene blends). |
| `hc_fuel_rate_mg_s` | `HC Fuel Rate (mg/s)` | `mg/s` | Mass flow rate of the **hydrocarbon component only** ($\text{C}_3\text{H}_6$ excluding $\text{N}_2$ inert in the 50% and 75% propylene mixtures; identical to `fuel_rate_mg_s` for pure fuels; `0` for 13 no-ignition/LOS rows). |

---

## 3. Allowed Enums & QA Flags Reference

### 3.1 Missing-Value Reasons (`*_missing_reason`)
- `unavailable_in_source` — the investigation did not measure or report this variable (or its unit is missing from the source header).
- `not_reported` — the column exists, but the cell is blank (`""`, `–`, `none`, `n/a`).
- `invalid_value` — physically impossible value (`0 mmHg` pressure in FLEX-114, `-1 ppm` CO in BASS-II, or `OR` sensor over-range).
- `not_parseable` — cell contains free text, ranges, or approximate values (`~6`, `5   3   1   <1`, `>500`).
- `pending_review` — numeric instrument reading exists (`Air display` in BASS-II), awaiting science sign-off on calibration formula before populating `flow_cm_s`.

### 3.2 Soft QA Flags (`qa_flags` in `runs.csv`)
- `impossible_value_nulled` — canonical value was physically impossible and blanked (`PSI-69:FLEX-114`, `pressure_raw = 0`).
- `gas_sum_off` — initial gas mole fractions ($\text{O}_2 + \text{N}_2 + \text{CO}_2 + \text{He}$) in FLEX sum outside $1.00 \pm 0.01$ (`6` rows sum to `0.98` due to rounding).
- `identifier_reused` — two distinct FLEX test numbers (`183` and `184`) share `FLEX Identifier = 193F001`.
- `fuel_label_normalised` — `fuel` differs from `fuel_raw` beyond simple upper/lowercase (e.g. `1/4" black rod` $\rightarrow$ `PMMA`, `75 % Propylene` $\rightarrow$ `75% propylene`).
- `negative_gas_reading` — BASS-II row had `-1` in `Initial CO (ppm)` (`13` rows).
- `date_year_typo_in_source` — BASS-II row has `2016` or `2018` in `Date` despite `GMT` day-of-year and experiment timeline being `2014` (`5` rows: `O20–O22`, `T9`, `T18`).
- `below_physical_range` — SPICE row has negative `flow_cm_s` (`-0.28` or `-5.92 cm/s`, `8` rows) caused by the negative intercept of the linear anemometer fit $u_{a,0} = 0.94 \cdot \text{AIR} - 5.92\text{ cm/s}$ at `AIR = 6` and `AIR = 0`.
- `time_unparsed` — non-blank ignition time cell could not be parsed as a clock time (e.g. `LOS`, `Ku LOS`, `no ku` in SPICE).
