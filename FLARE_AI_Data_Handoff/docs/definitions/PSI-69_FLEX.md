# PSI-69 — FLEX (Flame Extinguishment Experiment) Definitions & Notes

- **DOI:** `10.60555/mbq8-0451` (PSI Version 5, CC0-1.0)
- **Facility:** International Space Station (ISS) — Combustion Integrated Rack (CIR) / Multi-user Droplet Combustion Apparatus (MDCA)
- **Domain & Gravity:** `liquid_droplet`, `microgravity` (`274` rows in `PSI-69_Experimental table_FLEX.csv`)
- **Fuels:** `methanol` ($n = 119$), `heptane` ($n = 155$)

## Key Findings from Local NASA Documents
1. **Ambient Pressure Varies (`I-005`):**
   - `103` rows at `526.3–544.4 mmHg` (`70.17–72.58 kPa`, ~0.7 atm)
   - `161` rows at `752.0–774.1 mmHg` (`100.26–103.21 kPa`, ~1.0 atm)
   - `2` rows at `1545.7–1553.8 mmHg` (`206.08–207.16 kPa`, ~2.0 atm)
   - `7` rows at `2055.6–2319.9 mmHg` (`274.06–309.29 kPa`, ~2.7–3.0 atm)
   - `1` row (`Test #114`, `C11M201`) has an impossible `0 mmHg` (`I-020`), blanked to `NULL` with `missing_reason = invalid_value` and flagged `impossible_value_nulled`.
2. **`CO initial ambient composition; mole fraction` is Carbon Dioxide ($\text{CO}_2$, `I-002`):**
   - Confirmed by *FLEX_EIRD_v4.pdf* §5.1.4 (p. 38: *"Suppressant Type: CO2, He and SF6. Suppressant Mole Fraction: 0 – 0.7 ± 0.01"*) and *FLEX_Test_Plan.pdf* Tables 8, 11, and 12 (pp. 8, 14, 15: $X_{\text{N}_2} = 1.0 - X_{\text{O}_2} - X_{\text{CO}_2}$).
   - The CSV header stripped subscript `2` from all diatomic/triatomic gases (`O` = $\text{O}_2$, `N` = $\text{N}_2$, `CO` = $\text{CO}_2$).
3. **`Burning rate; mm` is the $d^2$-Law Burning Rate Constant $K$ in $\text{mm}^2/\text{s}$ (`I-001`):**
   - Confirmed by *FLEX_EIRD_v4.pdf* p. 20 & Table 13 (p. 76: $k$ in $\text{mm}^2/\text{s}$), and verified numerically against $(d_0^2 - d_{\text{ext}}^2)/t_{\text{burn}}$ across the table.
   - Because the raw CSV header omitted the exponent and `/s`, `value_num` is kept `NULL` (`unavailable_in_source`) in `run_measurements.csv` per strict contract rule, while the raw value (`0.05–1.06`) is preserved in `value_text`.
4. **Per-Test `.txt` Files (`97` files in `data/raw/PSI-69_FLEX/`):**
   - Eight calibration test points (`20CAL08`, `20CAL10`, `20CAL12`, `20CAL13`, `30CAL02`, `30CAL03`, `30CAL06`, `40CAL01` — matching `FLEX Test #1–8`) include time-series camera logs (`A`, `B`, `D`), `_Chamber_Gases.txt`, `_Chamber_Readings.txt`, `_Radiometer_Readings.txt`, and `_Testpoint_Settings.txt`.
