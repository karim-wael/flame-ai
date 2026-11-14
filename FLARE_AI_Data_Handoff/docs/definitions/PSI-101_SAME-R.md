# Per-Source Definitions & Provenance: `PSI-101` (SAME-R)

- **Investigation:** Smoke Aerosol Measurement Experiment — Reflight (`SAME-R`)
- **DOI:** `10.60555/2np7-jv14` · **License:** `CC0-1.0`
- **Hardware / Platform:** ISS Microgravity Science Glovebox (`MSG`, `109` microgravity flight runs) + NASA Glenn Research Center (`GRC`) Ground Verification & Drum Chambers (`60` normal-gravity `1g` ground runs)
- **Domain:** `smoke`
- **Raw Tables:** `data/raw/PSI-101_SAME-R/PSI-101_runs.csv` + `data/raw/PSI-101_SAME-R/Combined SAMER Results 06 02 14.xlsx` (`SAME R Results`, `Gnd Verif. 8-2012`, `Drum 8-2012` sheets)

---

## 1. Canonical Mapping (`runs.csv`)

| Canonical Field | Source Column | Rule / Unit Conversion |
|---|---|---|
| `run_id` | `SAME Test #` + `Sample Type` | `PSI-101:{Material}_{Test#}` for flight runs (e.g. `PSI-101:Kapton_51`), `PSI-101:GNDVERIF_{seq}` and `PSI-101:DRUM_{seq}` for 1g ground runs. |
| `gravity_regime` | Sheet / folder | `microgravity` for the `109` ISS flight runs (`SAME R Results` sheet); `normal_gravity` for the `60` post-flight ground baseline runs (`Gnd Verif. 8-2012` and `Drum 8-2012` sheets). |
| `fuel` | `Sample Type` | Normalised material name: `Kapton`, `Silicone`, `Teflon`, `Pyrell`, `Cotton lamp wick`, `Dibutyl phthalate (DBP)`. |
| `o2_vol_pct` | *(none)* | `NULL` (`o2_missing_reason = 'unavailable_in_source'`). Tests ran in ambient MSG / ground air (~21% O₂). |
| `pressure_kpa` | *(none)* | `NULL` (`pressure_missing_reason = 'unavailable_in_source'`). |
| `flow_cm_s` | `Inlet velocity (cm/s)` | Used as-is in `cm/s` (`0.0–8.1 cm/s`, `flow_basis = 'inlet'`). |
| `dup_of` & `qa_flags` | `SAME Test #` (`a` suffix) | `72` rows ending in `a` (e.g. `51a`, `61a`) are secondary-aging re-measurements of the same smoke cloud after extra aging time; `dup_of` points to the parent `run_id` and `qa_flags` includes `secondary_aging_remeasurement` (`I-027`). |

---

## 2. Long-Format Variables (`run_measurements.csv`)

| `variable` | Raw Column | Unit | Physical Meaning |
|---|---|---|---|
| `rt_r0` | `Rt/R0` | `ratio` | Heater wire resistance ratio ($R_t / R_0$), controlling sample pyrolysis temperature. |
| `heater_temp_c_derived` | `T ( C) - Eq. 2 of lrt` | `degC` | Derived sample heater temperature in °C from master workbook Eq. 2. |
| `heating_duration_s` | `Duration (sec)` | `s` | Sample heating / pyrolysis duration in seconds (blank on `a` secondary-aging rows by design). |
| `primary_aging_s` | `Primary aging time (sec)` | `s` | Primary smoke aging duration before dilution/measurement. |
| `primary_mixing_s` | `Primary mixing time (sec)` | `s` | Mixing fan duration inside aging chamber. |
| `net_aging_s` | `Net aging time (sec)` | `s` | Net aging time reported in the PSI summary CSV. |
| `net_aging_s_workbook` | `Net Aging  Duration` | `s` | Net aging time from `Combined SAMER Results 06 02 14.xlsx`. |
| `amd_um` | `M1/M0 (micro-m)--AMD` | `um` | Arithmetic mean particle diameter ($M_1 / M_0$) in micrometers. |
| `dam_um` | `Diameter of Average mass (micro-m)` | `um` | Diameter of average mass ($d_{\text{am}}$) in micrometers. |
| `hc_sigma_g` | `Hatch Choate Sigma g` | `unitless` | Geometric standard deviation ($\sigma_g$) from Hatch-Choate lognormal equations. |
| `hc_dg_um` | `Hatch Choate Dg` | `um` | Count median / geometric mean diameter ($d_g$) from Hatch-Choate equations in micrometers. |
| `m0_per_cm3` | `M0 best Diameter (#/cm3)` | `1/cm3` | Zeroth moment of particle size distribution (number concentration, $\text{particles/cm}^3$). |
| `m1_mm_per_cm3` | `M1 (mm/cm3)` | `mm/cm3` | First moment of particle size distribution (total particle diameter length per unit volume, $\text{mm/cm}^3$). |
| `mass_loss_mg` | `Mass Loss (mg)` | `mg` | Sample mass loss during pyrolysis in milligrams. |

---

## 3. Resolved Source Discrepancies (`I-026`)
- **Phantom `Teflon, 57` excluded:** In `PSI-101_Experimental table_SAME-R.csv`, row `Teflon, 57` is a copy-paste duplicate of `Lampwick, 57` (`Rt/R0 = 1.253`, which is a lampwick heater setting; Teflon runs use `~1.445`). Verified absent from `Combined SAMER Results 06 02 14.xlsx`.
- **Missing `Kapton, 112` restored:** Test `112` (`Kapton, low flow run w STS, Rt/R0 = 1.48, 2.0 cm/s`) is present in `Combined SAMER Results 06 02 14.xlsx` (`SAME R Results` row 122) and required to match the report's 109-flight-run total (`qa_flags = 'added_from_workbook'`).
