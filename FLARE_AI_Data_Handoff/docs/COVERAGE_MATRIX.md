# FLARE AI — Coverage & Research-Gap Matrix

**Owner:** Data Engineering (Farah El Qady, Salma)  
**Contract Version:** v0.3 · **ETL Version:** 0.1.0  
**Machine-readable file:** `processed/coverage.csv`

---

## 1. Executive Summary of Parameter Coverage

Across the **1,157 parsed runs** across all **6 NASA PSI investigations** (`1,100` unique runs after excluding `34` exact and `23` near duplicates in SPICE, plus `77` secondary-aging smoke re-measurements in `PSI-101`/`PSI-102`), each investigation covers **only 1 or 2 of the 3 canonical environmental axes**:

| Investigation | Domain | Gravity | Oxygen (`o2_vol_pct`) | Pressure (`pressure_kpa`) | Airflow (`flow_cm_s`) | Total Runs (`Unique`) |
|---|---|---|---|---|---|---|
| `PSI-69` **FLEX** | `liquid_droplet` | `microgravity` | **274 rows** (`12–34% vol`) | **273 rows** (`70.2–309.3 kPa`) | **0 rows** (`unavailable_in_source`) | 274 (`274`) |
| `PSI-25` **BASS-II** | `solid` | `microgravity` | **129 rows** (`13.6–27.8% vol`) | **0 rows** (`unavailable_in_source`) | **0 canonical** (`25` single-number `Air display` rows `pending_review`, `100` multi-step/free-text, `4` blank) | 129 (`129`) |
| `PSI-107` **SPICE** | `gas_jet` | `microgravity` | **0 rows** (`unavailable_in_source`, nominal ~21%) | **0 rows** (`unavailable_in_source`, nominal ~101 kPa) | **444 rows** (`-5.92` to `85.28 cm/s`; `25` blank) | 469 (`412`) |
| `PSI-101` **SAME-R** | `smoke` | `microgravity` (`109`), `normal_gravity` (`60`) | **0 rows** (`unavailable_in_source`) | **0 rows** (`unavailable_in_source`) | **169 rows** (`0.0–8.1 cm/s`) | 169 (`169`) |
| `PSI-102` **SAME** | `smoke` | `microgravity` (`64`), `normal_gravity` (`42`), `unknown` (`8`) | **0 rows** (`unavailable_in_source`) | **0 rows** (`unavailable_in_source`) | **102 rows** (`2.1–10.0 cm/s`; `12` blank `not_reported`) | 114 (`114`) |
| `PSI-98` **SAFFIRE-I** | `solid` | `microgravity` (Cygnus) | **2 rows** (`21.5–21.6% vol`) | **0 rows** (`unavailable_in_source`) | **2 rows** (`20.0 cm/s`) | 2 (`2`) |

> **Headline Takeaway for Malak & Zeiad:** No single downloaded investigation measures all three canonical variables (`o2_vol_pct`, `pressure_kpa`, `flow_cm_s`) simultaneously. FLEX owns the **O₂ × Pressure** plane (including **33 runs strictly >23% O₂** — or **35 runs at ≥23% O₂** — in the sub-atmospheric exploration habitat regime, ~70–73 kPa), SPICE (`PSI-107`) and SAME/SAME-R (`PSI-101`/`102`) own the **Airflow** axis (plus **102 normal-gravity 1g ground baseline runs** in SAME/SAME-R), SAFFIRE-I (`PSI-98`) provides **2 large-scale O₂ × Airflow (`20 cm/s`) solid burns**, and BASS-II (`PSI-25`) bridges **O₂ × Solid Fuels** (and will bridge **O₂ × Airflow** for 25 constant-flow runs if Malak approves `U = 1.0066 × Air display`).

---

## 2. Populated Parameter Cells (`total_runs > 0`)

| Cell ID | Gravity | Domain | O₂ Band | Pressure Band | Flow Band | Total (`Unique`) | Sources | Fuels | Status |
|---|---|---|---|---|---|---:|---|---|---|
| `COV-01` | `microgravity` | `gas_jet` | unmeasured_o2 | unmeasured_pressure | high_flow (>40 cm/s) | 126 (`107`) | `PSI-107` | 50% propylene, 75% propylene, ethylene, methane, propane, propylene | covered |
| `COV-02` | `microgravity` | `gas_jet` | unmeasured_o2 | unmeasured_pressure | low_flow (0-15 cm/s) | 97 (`87`) | `PSI-107` | 50% propylene, 75% propylene, propane, propylene | covered |
| `COV-03` | `microgravity` | `gas_jet` | unmeasured_o2 | unmeasured_pressure | moderate_flow (15-40 cm/s) | 213 (`191`) | `PSI-107` | 50% propylene, 75% propylene, ethylene, methane, propane, propylene | covered |
| `COV-04` | `microgravity` | `gas_jet` | unmeasured_o2 | unmeasured_pressure | unmeasured_or_quiescent | 25 (`19`) | `PSI-107` | 75% propylene, ethylene, propane, propylene | covered |
| `COV-05` | `microgravity` | `gas_jet` | unmeasured_o2 | unmeasured_pressure | zero_or_negative_cal (<=0 cm/s) | 8 (`8`) | `PSI-107` | 50% propylene, 75% propylene | covered |
| `COV-06` | `microgravity` | `liquid_droplet` | enriched_o2 (>23%) | near_atm (85-115 kPa / ~1 atm) | unmeasured_or_quiescent | 16 (`16`) | `PSI-69` | heptane, methanol | covered |
| `COV-07` | `microgravity` | `liquid_droplet` | enriched_o2 (>23%) | sub_atm (<85 kPa / ~0.7 atm) | unmeasured_or_quiescent | 33 (`33`) | `PSI-69` | heptane, methanol | covered |
| `COV-08` | `microgravity` | `liquid_droplet` | low_o2 (<19%) | near_atm (85-115 kPa / ~1 atm) | unmeasured_or_quiescent | 89 (`89`) | `PSI-69` | heptane, methanol | covered |
| `COV-09` | `microgravity` | `liquid_droplet` | low_o2 (<19%) | sub_atm (<85 kPa / ~0.7 atm) | unmeasured_or_quiescent | 26 (`26`) | `PSI-69` | heptane, methanol | covered |
| `COV-10` | `microgravity` | `liquid_droplet` | normoxic_o2 (19-23%) | elevated_pressure (>115 kPa / 2-3 atm) | unmeasured_or_quiescent | 9 (`9`) | `PSI-69` | heptane, methanol | covered |
| `COV-11` | `microgravity` | `liquid_droplet` | normoxic_o2 (19-23%) | near_atm (85-115 kPa / ~1 atm) | unmeasured_or_quiescent | 56 (`56`) | `PSI-69` | heptane, methanol | covered |
| `COV-12` | `microgravity` | `liquid_droplet` | normoxic_o2 (19-23%) | sub_atm (<85 kPa / ~0.7 atm) | unmeasured_or_quiescent | 44 (`44`) | `PSI-69` | heptane, methanol | covered |
| `COV-13` | `microgravity` | `liquid_droplet` | normoxic_o2 (19-23%) | unmeasured_pressure | unmeasured_or_quiescent | 1 (`1`) | `PSI-69` | methanol | sparse (<5 unique runs) |
| `COV-14` | `microgravity` | `smoke` | unmeasured_o2 | unmeasured_pressure | low_flow (0-15 cm/s) | 151 (`151`) | `PSI-101;PSI-102` | Cotton lamp wick, Dibutyl phthalate (DBP), Kapton, Pyrell, Silicone, Teflon | covered |
| `COV-15` | `microgravity` | `smoke` | unmeasured_o2 | unmeasured_pressure | zero_or_negative_cal (<=0 cm/s) | 22 (`22`) | `PSI-101` | Cotton lamp wick, Kapton, Pyrell, Silicone, Teflon | covered |
| `COV-16` | `microgravity` | `solid` | low_o2 (<19%) | unmeasured_pressure | pending_calibration (raw setting only) | 12 (`12`) | `PSI-25` | PMMA, SIBAL | covered |
| `COV-17` | `microgravity` | `solid` | low_o2 (<19%) | unmeasured_pressure | unmeasured_or_quiescent | 66 (`66`) | `PSI-25` | PMMA, SIBAL, wax candle | covered |
| `COV-18` | `microgravity` | `solid` | normoxic_o2 (19-23%) | unmeasured_pressure | moderate_flow (15-40 cm/s) | 2 (`2`) | `PSI-98` | SIBAL fabric (75% cotton / 25% fiberglass) | sparse (<5 unique runs) |
| `COV-19` | `microgravity` | `solid` | normoxic_o2 (19-23%) | unmeasured_pressure | pending_calibration (raw setting only) | 13 (`13`) | `PSI-25` | Nomex, PMMA, SIBAL | covered |
| `COV-20` | `microgravity` | `solid` | normoxic_o2 (19-23%) | unmeasured_pressure | unmeasured_or_quiescent | 38 (`38`) | `PSI-25` | PMMA, SIBAL | covered |
| `COV-21` | `normal_gravity` | `smoke` | unmeasured_o2 | unmeasured_pressure | low_flow (0-15 cm/s) | 94 (`94`) | `PSI-101;PSI-102` | Cotton lamp wick, Dibutyl phthalate (DBP), Kapton, Pyrell, Silicone, Teflon | covered |
| `COV-22` | `normal_gravity` | `smoke` | unmeasured_o2 | unmeasured_pressure | unmeasured_or_quiescent | 8 (`8`) | `PSI-102` | Cotton lamp wick, Dibutyl phthalate (DBP), Kapton, Silicone, Teflon | covered |
| `COV-23` | `unknown` | `smoke` | unmeasured_o2 | unmeasured_pressure | low_flow (0-15 cm/s) | 4 (`4`) | `PSI-102` | Teflon | sparse (<5 unique runs) |
| `COV-24` | `unknown` | `smoke` | unmeasured_o2 | unmeasured_pressure | unmeasured_or_quiescent | 4 (`4`) | `PSI-102` | Cotton lamp wick, Dibutyl phthalate (DBP), Kapton, Silicone | sparse (<5 unique runs) |

---

## 3. Critical Research & Archive Gaps (`total_runs = 0`)

| Gap ID | Gravity | Domain | O₂ Band | Pressure Band | Flow Band | Why It Matters |
|---|---|---|---|---|---|---|
| `GAP-25` | `partial_gravity` | `liquid_droplet` | ALL (especially >23% O2) | sub_atm (<85 kPa / ~0.7 atm) | ALL | CRITICAL GAP: Zero Lunar (~0.16g) or Martian (~0.38g) partial-gravity droplet combustion runs in PSI archive. |
| `GAP-26` | `partial_gravity` | `solid` | ALL (especially >23% O2) | sub_atm (<85 kPa / ~0.7 atm) | ALL | CRITICAL GAP: Zero Lunar (~0.16g) or Martian (~0.38g) partial-gravity solid flammability runs in PSI archive. |
| `GAP-27` | `partial_gravity` | `gas_jet` | ALL | ALL | ALL | CRITICAL GAP: Zero Lunar/Martian partial-gravity gas-jet smoke-point runs in PSI archive. |
| `GAP-28` | `partial_gravity` | `smoke` | ALL | ALL | ALL | CRITICAL GAP: Zero Lunar/Martian partial-gravity smoke aerosol detector runs in PSI archive. |
| `GAP-29` | `microgravity` | `solid` | enriched_o2 (>23%) | sub_atm (<85 kPa / ~0.7 atm) | ALL | CRITICAL GAP: Exploration habitat atmosphere (<=10.2 psi / ~70 kPa + enriched O2) has 35 FLEX droplet runs but 0 solid runs (BASS-II and SAFFIRE-I operated at ~1 atm / ~21% O2 and did not record per-run pressure in CSV). |
| `GAP-30` | `microgravity` | `smoke` | low_o2 / enriched_o2 | sub_atm / elevated_pressure | ALL | INSTRUMENTATION GAP: Smoke aerosol investigations PSI-101 (SAME-R, 169 rows) and PSI-102 (SAME, 114 rows) report airflow (0-10 cm/s) across ISS microgravity and 1g ground baselines, but 0 per-run O2 or pressure values. |
| `GAP-31` | `microgravity` | `liquid_droplet` | ALL | ALL | low/moderate/high_flow (>0 cm/s) | INSTRUMENTATION GAP: FLEX CSV reports 0 flow_cm_s values (droplets burned in quiescent chamber or slow translating-fiber drift not tabulated in CSV). |
| `GAP-32` | `microgravity` | `gas_jet` | low_o2 / enriched_o2 | sub_atm / elevated_pressure | ALL | INSTRUMENTATION GAP: SPICE CSV reports 0 per-run O2 or pressure values (operated in nominal ISS MSG air ~101 kPa, 21% O2). |
| `GAP-33` | `normal_gravity` | `liquid_droplet / solid / gas_jet` | ALL | ALL | ALL | BASELINE GAP IN FLIGHT CSVs: While PSI-101 (60 rows) and PSI-102 (42 rows) include 102 normal-gravity (1g) smoke ground runs, FLEX/BASS-II/SAFFIRE-I/SPICE CSVs contain 0 1g rows (36 1g SPICE rows exist in Dotson_umd_0117N_10980.pdf Tables 6.3-6.4, issue I-025). |
