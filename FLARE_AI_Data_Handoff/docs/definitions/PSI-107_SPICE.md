# PSI-107 — SPICE (Smoke Point In Co-flow Experiment) Definitions & Notes

- **DOI:** `10.60555/9kbh-e962` (PSI Version 4, CC0-1.0)
- **Facility:** International Space Station (ISS) — Microgravity Science Glovebox (MSG)
- **Domain & Gravity:** `gas_jet`, `microgravity` (`469` rows in `PSI-107_Experimental table_Spice.csv`)
- **Fuels:** `ethylene` (`47`), `propane` (`50`), `propylene` (`122`), `75% propylene` (`135`, 75% $\text{C}_3\text{H}_6$ / 25% $\text{N}_2$ by mole), `50% propylene` (`111`, 50% $\text{C}_3\text{H}_6$ / 50% $\text{N}_2$ by mole), `methane` (`4`)

## Key Findings from Local NASA Documents
1. **Flight Year Confirmed as `2009` (`I-014`):**
   - *SPICE Final Report 12_2_2012.pdf* (p. 13) and *Dotson_umd_0117N_10980.pdf* (p. 22, Table 6.1 p. 67) state that all 12 SPICE flight sessions in the ISS MSG took place between **February 14, 2009 (`GMT date = 45`) and June 23, 2009 (`GMT date = 174`)**.
   - `test_date` is populated as `2009-MM-DD`, while `test_date_raw` preserves the raw integer day-of-year (`45–174`).
2. **Why `Air Rate (cm/s)` Has 8 Negative Values (`-0.28` and `-5.92 cm/s`, `I-016`):**
   - *Dotson_umd_0117N_10980.pdf* §3.1.1 (Figure 3.4, p. 27) shows that `Air Rate (cm/s)` at 13 mm above the burner tip is calculated from the onboard integer `AIR` video display reading via the linear calibration fit:
     $$u_{a,0} = 0.94 \times \text{AIR} - 5.92\text{ cm/s}$$
   - When the integer `AIR` reading is `0` (fan off / still air, 3 rows on day 167), the formula outputs `-5.92 cm/s`. When `AIR = 6` (very low flow, 5 rows on day 136), it outputs `-0.28 cm/s`.
   - Values are kept in `flow_cm_s` and flagged `below_physical_range` for Malak to decide whether to clamp to `0 cm/s`.
3. **Why 469 CSV Rows vs 526 Flames in the PSI Description (`I-012`):**
   - *SPICE Final Report 12_2_2012.pdf* (p. 14) states that 526 flames were studied in total (recorded in *Spice Flight Test data II.xls* Appendix A), and *Dotson_umd_0117N_10980.pdf* Table 3.1 (p. 23) reports **52 microgravity smoke-point summary flames** across the fuels. The 469 rows in `PSI-107_Experimental table_Spice.csv` are the individual test-point rows exported from the main worksheet (`469 + 52 = 521`, plus header/notes).
4. **Exact & Near Duplicates (`I-013`, `I-021`):**
   - `34` rows are exact duplicates (across `31` groups of identical rows; some groups have 3–4 copies because multiple still/video frames were logged for the same flame condition).
   - `23` rows are near-duplicates (same day, ignition time, fuel, and nozzle, with flow/fuel numbers within 2% or ignition time formatted with dots `14.48.19` vs colons `14:48:19`).
5. **Normal-Gravity (`1g`) Ground Data in Dotson's Thesis (`I-025`):**
   - While `PSI-107_Experimental table_Spice.csv` is 100% ISS microgravity data, *Dotson_umd_0117N_10980.pdf* Appendix 6.3 (pp. 70–71) contains **36 normal-gravity (`1g`) smoke-point rows**: Table 6.3 (`15` tests using the SPICE prototype module on Earth at UMD) and Table 6.4 (`21` tests in an unconfined coflow burner).
