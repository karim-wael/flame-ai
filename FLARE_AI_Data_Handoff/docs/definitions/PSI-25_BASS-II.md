# PSI-25 — BASS-II (Burning and Suppression of Solids II) Definitions & Notes

- **DOI:** `10.60555/4qc4-de67` (PSI Version 4, CC0-1.0)
- **Facility:** International Space Station (ISS) — Microgravity Science Glovebox (MSG) flow duct
- **Domain & Gravity:** `solid`, `microgravity` (`129` rows in `PSI-25_Experimental table_BASS-II.csv`)
- **Principal Investigators:** Bhattacharjee (`B1–B36`), Ferkul (`F1–F4`), Miller (`M1–M20`), Olson (`O1–O22`), Fernandez-Pello (`P1–P25`), T'ien (`T1–T29`)

## Key Findings from Local NASA Documents
1. **All 28 Unlabeled Rod / Film / Spherical Samples Confirmed as `PMMA` (`I-019`):**
   - *BASS-II data FAQ.docx* explicitly states:
     - **Bhattacharjee:** thin **PMMA** films (`100–400 micron`)
     - **Ferkul:** **Nomex III** (`3` rows) and **Japan Wax candle** (`1` row)
     - **Miller:** thick **PMMA** slabs (`1–5 mm`)
     - **Olson:** clear and black **PMMA** rods (`1/4"`, `3/8"`, `1/2"`)
     - **Fernandez-Pello:** black and clear **PMMA** rods (`1/4"`, `3/8"`, `0.5"`)
     - **T'ien:** **SIBAL** fabric (75/25 cotton/fiberglass blend, `27` rows) + `1` sample / `2` tests (`T3`, `T7`, Sample `182m`) with `4 cm spherical section` = **PMMA**.
   - Result: all 129 rows map cleanly to `PMMA` (`98`), `SIBAL` (`27`), `Nomex` (`3`), and `wax candle` (`1`), with full geometry/color preserved in `fuel_detail`.
2. **Airflow Calibration & `Air display` (`I-006`, `I-007`):**
   - *BASS-II data FAQ.docx* defines `Fan display` as instantaneous fan voltage $\times 10$ (max `122` = `12.2 V`) or control-box potentiometer (`pot`, max `10`), and `Air display` as duct velocity readout on the video display (`~1 min` response time).
   - *Fan calibration data.xlsx* provides per-restrictor lookup tables and the formula $U\text{ (cm/s)} = 1.0066 \times \text{Air display}$, noting it is based on SPICE fan calibration data at 56 mm downstream, 36 mm from bottom (centerline).
   - Until Malak approves applying $U = 1.0066 \times \text{Air display}$ for the 49 single-number rows, `flow_cm_s` stays `NULL` with `missing_reason = pending_review` (and `not_parseable` for the 80 multi-step/text rows).
3. **Sensor Artifacts & Date Typos (`I-010`, `I-024`):**
   - `Initial CO (ppm)` has `-1` on 13 rows (sensor zero-offset) and `OR` (`>1000 ppm` over-range on CSA-CP sensor per *BASS-II data FAQ.docx*). Both are set to `value_num = NULL` + `invalid_value`.
   - Five rows (`O20–O22` with `2/26/2016`, `T9` and `T18` with `6/24/2018`) have year typos in `Date` where `GMT` day-of-year (`57` and `175`) confirms `2014`. Flagged `date_year_typo_in_source`.
