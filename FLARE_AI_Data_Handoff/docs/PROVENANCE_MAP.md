# FLARE AI — Provenance & Lineage Map

**Owner:** Data Engineering (Farah El Qady, Salma)  
**Contract Version:** v0.3  

Every row and every number in `processed/` traces back to an immutable, SHA-256-locked file in `data/raw/`. This document maps each source file, its checksum, its column-level transformation into `runs.csv` and `run_measurements.csv`, and the supporting NASA documents that verify each rule.

---

## 1. Raw Experimental Table Fingerprints

| `source_id` | Investigation | Raw CSV Path | Encoding | Data Rows | SHA-256 Checksum (`data/raw_manifest.csv`) |
|---|---|---|---|---|---|
| `PSI-69` | FLEX | `data/raw/PSI-69_FLEX/PSI-69_Experimental table_FLEX.csv` | `cp1252` | 274 | `37c88ce8ae9391b7544ff630a45ce87543d04d317cdbfbed104fe7d5c27e1b96` |
| `PSI-25` | BASS-II | `data/raw/PSI-25_BASS-II/PSI-25_Experimental table_BASS-II.csv` | `utf-8-sig` | 129 | `71e792bf6b5fb5ea620c5dd70fbbac05515992e12aefcf5dff47312caa48c042` |
| `PSI-107` | SPICE | `data/raw/PSI-107_SPICE/PSI-107_Experimental table_Spice.csv` | `utf-8-sig` | 469 | `fb0d7e60cf5367afb429089e9901d27288f78038efd26c8de1db4fbe04117136` |
| `PSI-101` | SAME-R | `data/raw/PSI-101_SAME-R/PSI-101_runs.csv` | `utf-8` | 169 | `1649c01321a6be9bc091eb906d5be8cf95ab7311e3de45c95e27e2ec5a822d84` |
| `PSI-102` | SAME | `data/raw/PSI-102_SAME/PSI-102_runs.csv` | `utf-8` | 114 | `cf433c09cdab59029fc6ca5dc1d0eb93a0cdab149e9df9e546d227efaa1ba286` |
| `PSI-98` | SAFFIRE-I | `data/raw/PSI-98_SAFFIRE-I/PSI-98_runs.csv` | `utf-8` | 2 | `855d0ff11e74dc8135b8c6b9459ce9bc1df8995a72729ab59a32f9fa9a67fb4a` |

---

## 2. Column-to-Canonical Provenance Map

| Source ID | Raw Column Header | Target Table | Target Column / Variable | Transformation Rule | Verification Document |
|---|---|---|---|---|---|
| `PSI-69` | `FLEX Test #` | `runs.csv` | `run_id`, `native_test_id` | `PSI-69:FLEX-<int:03d>` (`1` → `PSI-69:FLEX-001`) | Raw table primary index |
| `PSI-69` | `FLEX Identifier` | `run_measurements.csv` | `flex_identifier` | Trimmed text (`20CAL08`); links to per-test `.txt` files (`<ID>.txt`, `<ID>_Chamber_Readings.txt`, etc.) | *FLEX DoD.docx* |
| `PSI-69` | `Test Date` | `runs.csv` | `test_date`, `test_date_raw` | `M/D/YYYY` → `YYYY-MM-DD` (`3/5/2009` → `2009-03-05`) | Raw table |
| `PSI-69` | `Test GMT` | `runs.csv` | `test_time_gmt` | Zero-padded `HH:MM:SS` (`1 row` blank → `""`) | Raw table |
| `PSI-69` | `Fuel` | `runs.csv` | `fuel`, `fuel_raw` | Lowercased (`Methanol` → `methanol`, `Heptane` → `heptane`) | *FLEX_EIRD_v4.pdf* §5.1.1 (p. 35) |
| `PSI-69` | `Ambient pressure; mmHg` | `runs.csv` | `pressure_kpa`, `pressure_raw` | $\text{kPa} = \text{mmHg} \times 0.133322$; Test 114 (`0 mmHg`) → `NULL` + `invalid_value` (`I-020`) | *FLEX_EIRD_v4.pdf* §5.2.8 (p. 44) |
| `PSI-69` | `O initial ambient composition; mole fraction` | `runs.csv` | `o2_vol_pct`, `o2_raw` | $\text{vol \%} = \text{mole fraction} \times 100$, `o2_basis = initial` | *FLEX_EIRD_v4.pdf* §5.1.4 (p. 38) |
| `PSI-69` | `N initial ambient composition; mole fraction` | `run_measurements.csv` | `n2_initial_mole_fraction` | Numeric float (`mole fraction`); subscript `2` stripped in raw header | *FLEX_EIRD_v4.pdf* §5.1.5 (p. 38) |
| `PSI-69` | `CO initial ambient composition; mole fraction` | `run_measurements.csv` | `co_initial_mole_fraction` | Numeric float (`mole fraction`); **physical gas is $\text{CO}_2$ suppressant** (subscript `2` stripped in raw header, `I-002`) | *FLEX_EIRD_v4.pdf* §5.1.4 (p. 38); *FLEX_Test_Plan.pdf* Tables 8, 11, 12 |
| `PSI-69` | `He initial ambient composition; mole fraction` | `run_measurements.csv` | `he_initial_mole_fraction` | Numeric float (`mole fraction`) | *FLEX_Test_Plan.pdf* Table 9 (p. 10) |
| `PSI-69` | `Droplet initial diameter; mm` | `run_measurements.csv` | `droplet_initial_diameter` | Numeric float (`mm`); Windows en-dash `–` → `NULL` + `not_reported` | *FLEX_EIRD_v4.pdf* §5.1.2 (p. 37) |
| `PSI-69` | `Visible flame extinction diameter; mm` | `run_measurements.csv` | `flame_extinction_diameter` | Numeric float (`mm`); blank/`–` → `NULL` + `not_reported` | *FLEX_EIRD_v4.pdf* Table 3 (p. 33) |
| `PSI-69` | `Burning rate; mm` | `run_measurements.csv` | `burning_rate_raw` | `value_num = NULL` + `unavailable_in_source` (raw header missing `/s` and exponent; document unit is $\text{mm}^2/\text{s}$, `I-001`); raw number kept in `value_text` | *FLEX_EIRD_v4.pdf* p. 20 & Table 13 (p. 76) |
| `PSI-69` | `Burn time; s` | `run_measurements.csv` | `burn_time` | Numeric float (`s`); `~6` and `~9` → `NULL` + `not_parseable` (`I-023`) | Raw table |
| `PSI-69` | `Test end` | `runs.csv` | `outcome_raw` | Trimmed text (`Disruption`, `Extinction`, `Completion`) | Raw table |
| `PSI-25` | `Test #` | `runs.csv` | `run_id`, `native_test_id` | `PSI-25:<Test #>` (`B1` → `PSI-25:B1`, `T28a` → `PSI-25:T28a`) | *BASS-II data FAQ.docx* |
| `PSI-25` | `PI` | `run_measurements.csv` | `principal_investigator` | Text (`Bhattacharjee`, `Ferkul`, `Fernandez-Pello`, `Miller`, `Olson`, `T'ien`) | *BASS-II data FAQ.docx* |
| `PSI-25` | `Date` | `runs.csv` | `test_date`, `test_date_raw` | `M/D/YYYY` → `YYYY-MM-DD`; 5 rows with `2016`/`2018` flagged `date_year_typo_in_source` (`I-024`) | *BASS-II data FAQ.docx*; *BASS-II Test Matrix by PI Final.xlsx* |
| `PSI-25` | `GMT` | `run_measurements.csv` | `gmt_day_of_year` | Day of year (`45–216` in 2014); stored as measurement, not clock time | *BASS-II data FAQ.docx* |
| `PSI-25` | `Sample #` | `run_measurements.csv` | `sample_number` | Sample card/rod ID (`128–244`, with `m`/`M`/`L` suffixes kept in `value_text`) | *BASS-II data FAQ.docx* |
| `PSI-25` | `Fuel Sample Material` | `runs.csv` | `fuel`, `fuel_raw`, `fuel_detail` | Mapped to `PMMA`, `SIBAL`, `Nomex`, `wax candle` as confirmed by *BASS-II data FAQ.docx* (`I-019`); full geometry kept in `fuel_detail` | *BASS-II data FAQ.docx* |
| `PSI-25` | `Flow restrictor` | `run_measurements.csv` | `flow_restrictor_count` | Integer `0`, `1`, `2` (`0` = highest flow, `2` = lowest flow) | *BASS-II data FAQ.docx* |
| `PSI-25` | `Fan display` | `run_measurements.csv` | `fan_display` | Raw text (voltage $\times 10$ or pot setting) | *BASS-II data FAQ.docx*; *Fan calibration data.xlsx* |
| `PSI-25` | `Air display` | `runs.csv` & `run_measurements.csv` | `flow_raw`, `air_display` | `flow_cm_s = NULL` + `pending_review` (single number) or `not_parseable` (multi-step text) awaiting approval of $U = 1.0066 \times \text{Air display}$ (`I-006/007`) | *Fan calibration data.xlsx*; *BASS-II data FAQ.docx* |
| `PSI-25` | `Radiometer gain   (1000   250   50   10)` | `run_measurements.csv` | `radiometer_gain` | Numeric (`10`, `50`, `250`, `1000`) or multi-step text in `value_text` | *BASS-II data FAQ.docx* |
| `PSI-25` | `Total Frames Shot` | `run_measurements.csv` | `total_frames_shot` | Numeric count; `none` → `not_reported`, `video`/`300+ +102` → `not_parseable` (`I-009`) | *BASS-II data FAQ.docx* |
| `PSI-25` | `Calibrated  initial O2 % by vol ` | `runs.csv` | `o2_vol_pct`, `o2_raw` | Direct `% by vol` (`13.6–27.8%`), `o2_basis = initial` | *BASS-II data FAQ.docx* |
| `PSI-25` | `Calibrated final O2 % by vol` | `run_measurements.csv` | `o2_final_vol_pct` | Numeric `% by vol` (`0.6–40.4%`) | *BASS-II data FAQ.docx* |
| `PSI-25` | `Initial CO2 % by vol` / `Final CO2 % by vol` | `run_measurements.csv` | `co2_initial_vol_pct`, `co2_final_vol_pct` | Numeric `% by vol` from CDM sensor | *BASS-II data FAQ.docx* |
| `PSI-25` | `Initial CO (ppm)` / `Final CO (ppm)` | `run_measurements.csv` | `co_initial_ppm`, `co_final_ppm` | Numeric `ppm` from CSA-CP sensor; `-1` and `OR` (`>1000 ppm`) → `NULL` + `invalid_value` (`I-010`) | *BASS-II data FAQ.docx* |
| `PSI-107` | *(synthetic)* | `runs.csv` | `run_id` | `PSI-107:D<day>-<HHMMSS\|NOTIME>-R<row:03d>` (`I-014`) | Deterministic row key |
| `PSI-107` | `GMT date` | `runs.csv` & `run_measurements.csv` | `test_date`, `test_date_raw`, `gmt_day_of_year` | Day of year (`45–174`) + confirmed flight year `2009` → `2009-02-14` to `2009-06-23` (`I-014`) | *SPICE Final Report 12_2_2012.pdf* p. 13; *Dotson thesis* p. 22 |
| `PSI-107` | `GMT ignition` | `runs.csv` & `run_measurements.csv` | `test_time_gmt`, `gmt_ignition_raw` | Normalized `HH:MM:SS` or `HH:MM`; `LOS`/`Ku LOS`/`no ku`/`n/a` → `""` + `time_unparsed` | Raw table |
| `PSI-107` | `GMT  Flame Off ` | `run_measurements.csv` | `gmt_flame_off_raw` | Raw text preserved | Raw table |
| `PSI-107` | `Fuel` | `runs.csv` | `fuel`, `fuel_raw` | Lowercased, `%` spacing normalized (`75 % Propylene` → `75% propylene`, `I-015`) | *SPICE RPT-002* p. A-19 |
| `PSI-107` | `Nozzle (mm)` | `run_measurements.csv` | `nozzle_diameter` | Numeric `mm` (`0.4064`, `0.762`, `1.6002`) | *SPICE RPT-002* p. A-7; *Dotson thesis* p. 22 |
| `PSI-107` | `Fuel Rate (sccm)` | `run_measurements.csv` | `fuel_rate_sccm` | Numeric `sccm` (K-factor corrected Sierra MFC flow) | *Dotson thesis* §3.1.2, Table 3.2 (p. 28) |
| `PSI-107` | `Fuel Rate (mg/s)` | `run_measurements.csv` | `fuel_rate_mg_s` | Numeric `mg/s` (total mixture mass flow) | *Dotson thesis* p. 23 |
| `PSI-107` | `HC Fuel Rate (mg/s)` | `run_measurements.csv` | `hc_fuel_rate_mg_s` | Numeric `mg/s` (hydrocarbon-only mass flow, `I-017`) | Raw table |
| `PSI-107` | `Air Rate (cm/s)` | `runs.csv` | `flow_cm_s`, `flow_raw` | Direct `cm/s` (`co-flow air velocity`); 8 negative values (`-0.28`, `-5.92` from linear fit $0.94 \cdot \text{AIR} - 5.92$) kept and flagged `below_physical_range` (`I-016`) | *Dotson thesis* §3.1.1, Fig. 3.4 (p. 27) |
