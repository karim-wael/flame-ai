# Per-Source Definitions & Provenance: `PSI-98` (SAFFIRE-I)

- **Investigation:** Spacecraft Fire Experiment I (`SAFFIRE-I`)
- **DOI:** `10.60555/0t15-1z43` · **License:** `CC0-1.0`
- **Hardware / Platform:** Free-flying **Cygnus (`OA-6`)** cargo vehicle after undocking from ISS (`platform = 'Cygnus'`, `gravity_regime = 'microgravity'`)
- **Domain:** `solid`
- **Raw Tables:** `data/raw/PSI-98_SAFFIRE-I/PSI-98_runs.csv` + `data/raw/PSI-98_SAFFIRE-I/metadata_conflicts.csv`

---

## 1. Canonical Mapping (`runs.csv`)

| Canonical Field | Source Column | Rule / Unit Conversion |
|---|---|---|
| `run_id` | `Sample Number` | `PSI-98:S1` (concurrent flow burn) and `PSI-98:S2` (opposed flow burn). Note: the 3 non-burn flow-visualization image sets in the raw CSV are excluded from `runs.csv`. |
| `platform` | Verified hardware docs | `Cygnus` (the PSI web portal erroneously lists `ISS` due to a copy-paste of `PSI-102` metadata, `I-030`). |
| `test_date` | Image-log UTC epoch timestamps | `2016-06-14` (`S1`: `20:44:58–20:55:03 UTC`; `S2`: `20:56:33–21:06:38 UTC`). |
| `fuel` | `Material` | `SIBAL fabric (75% cotton / 25% fiberglass)` |
| `o2_vol_pct` | `Percent O2` | `21.6` for `S1` (midpoint of `"21.5 - 21.7"`, `o2_basis = 'range_midpoint'`) and `21.5` for `S2` (`"~ 21.5"`, `o2_basis = 'approximate'`). Raw text kept in `o2_raw`. |
| `pressure_kpa` | *(none in CSV)* | `NULL` (`pressure_missing_reason = 'unavailable_in_source'`). |
| `flow_cm_s` | `Air Flow (cm/s)` | `20` (`20.0 cm/s`, `flow_basis = 'duct'`). |

---

## 2. Long-Format Variables (`run_measurements.csv`)

| `variable` | Raw Column | Unit | Physical Meaning |
|---|---|---|---|
| `flow_direction` | `Flow Direction` | *(text)* | `concurrent` (`S1`) or `opposed` (`S2`). |
| `o2_vol_pct_low` | `Percent O2` | `% vol` | Lower bound of reported oxygen range (`21.5`). |
| `o2_vol_pct_high` | `Percent O2` | `% vol` | Upper bound of reported oxygen range (`21.7` on `S1`, `21.5` on `S2`). |
| `ignition_power_w` | `Ignition Power (W)` | `W` | Hot-wire igniter electrical power (`182.0 W`). |
| `ignition_time_s` | `Ignition Time (s)` | `s` | Igniter energization duration (`8.0 s`). |
| `burn_time_s` | `Burn Time (s)` | `s` | Total burn duration (`420.0 s` on `S1`, `70.0 s` on `S2`). |
| `sample_length_mm` | `Sample Width (cm)` (swapped) | `mm` | True sample length (`940.0 mm` = `0.94 m`; swapped in raw CSV, `I-030`). |
| `sample_width_mm` | `Sample Length (cm)` (swapped) | `mm` | True sample width (`406.0 mm` = `0.406 m`; swapped in raw CSV, `I-030`). |
| `sample_thickness_mm` | `Sample Thickness (cm)` | `mm` | Reported thickness converted from cm (`3.7 mm`), flagged `suspect_thickness_unit` (`I-031`, likely `0.37 mm`). |
