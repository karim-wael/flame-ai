# Per-Source Definitions & Provenance: `PSI-102` (SAME)

- **Investigation:** Smoke Aerosol Measurement Experiment (`SAME`)
- **DOI:** `10.60555/gd4k-8h62` · **License:** `CC0-1.0`
- **Hardware / Platform:** ISS Microgravity Science Glovebox (`MSG`, `64` microgravity flight runs in 2007) + NASA GRC Ground Chamber (`42` normal-gravity `1g` ground runs) + `8` summary rows from `PSI-102_Experimental table_SAME.csv` (`gravity_regime = 'unknown'`)
- **Domain:** `smoke`
- **Raw Tables:** `data/raw/PSI-102_SAME/PSI-102_runs.csv` + `data/raw/PSI-101_SAME-R/Combined SAMER Results 06 02 14.xlsx` (`SAME1 Flight Tests 8-27-09` and `SAME Ground Test Results` sheets)

---

## 1. Canonical Mapping (`runs.csv`)

| Canonical Field | Source Column | Rule / Unit Conversion |
|---|---|---|
| `run_id` | Sheet prefix + Test ID | `PSI-102:FLIGHT_{id}` (`64` ISS microgravity rows), `PSI-102:GROUND_{id}` (`42` 1g ground rows), `PSI-102:TABLE_{id}` (`8` PSI CSV summary rows). |
| `gravity_regime` | Sheet / table | `microgravity` (`FLIGHT_*`), `normal_gravity` (`GROUND_*`), `unknown` (`TABLE_*`, where the summary CSV does not state flight vs. ground). |
| `fuel` | `Sample Type` / `Sample Material` | Normalised material name: `Kapton`, `Silicone`, `Teflon`, `Pyrell`, `Cotton lamp wick`, `Dibutyl phthalate (DBP)`. |
| `o2_vol_pct` | *(none)* | `NULL` (`o2_missing_reason = 'unavailable_in_source'`). |
| `pressure_kpa` | *(none)* | `NULL` (`pressure_missing_reason = 'unavailable_in_source'`). |
| `flow_cm_s` | `Inlet Velocity (cm/sec)` / `Air Flow (cm/s)` | Used as-is in `cm/s` (`2.1–10.0 cm/s`, `flow_basis = 'inlet'`). `12` blank rows (`8` ground secondary-aging rows + `4` `"same conditions as 1-4"` rows) are `NULL` with `flow_missing_reason = 'not_reported'` (`I-029`). |

---

## 2. Long-Format Variables (`run_measurements.csv`)

Includes all aerosol moment and Hatch-Choate variables defined in [PSI-101_SAME-R.md](file:///c:/Users/LOQ/OneDrive/Documents/HACKATHON/docs/definitions/PSI-101_SAME-R.md), plus:

| `variable` | Raw Column | Unit | Physical Meaning |
|---|---|---|---|
| `dam_dusttrak_a_um` | `DTRak A Diameter of average mass micrometers` | `um` | Ground-test DustTrak A diameter of average mass ($\mu\text{m}$). |
| `dam_dusttrak_b_um` | `DTRak B Diameter of average mass micrometers` | `um` | Ground-test DustTrak B diameter of average mass ($\mu\text{m}$). |
| `cmd_um` | `Best Diameter Ion A/Ptrak Count Mean Diamter (microns)` | `um` | Ground-test count mean diameter ($\mu\text{m}$) from Ion A / P-Trak. |
| `weight_loss_rate_mg_min` | `Weight loss rate (mg/min)` | `mg/min` | Sample mass loss rate in `mg/min` (`PSI-102:TABLE_1..4`). |
| `aging_duration_s` | `Aging Duration (minutes)` | `s` | Aging duration converted from minutes ($\times 60$) on `PSI-102:TABLE_1..4`. |

---

## 3. Logged Anomalies (`I-028`, `I-029`)
- **Out-of-range flow (`I-028`):** `PSI-102:TABLE_4` and `PSI-102:GROUND_24S` report `flow_cm_s > 8.0 cm/s` (`10.0` and `8.2 cm/s`), above the `2–8 cm/s` nominal hardware range; kept as reported and flagged `outside_documented_hardware_range`.
- **Unfilled `"same conditions as 1-4"` rows (`I-029`):** Rows `TABLE_5` through `TABLE_8` state `"same conditions as 1-4"` with blank numeric cells; kept `NULL` (`not_reported`) without guessing which of rows 1–4 was intended.
