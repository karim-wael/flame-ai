# FLARE AI — Test Fixtures (`fixtures/`)

**Owners:** Data Engineering (Farah El Qady, Salma)  
**Contract Version:** `v0.3` · **ETL Version:** `0.1.0`

This folder contains lightweight, deterministic sample files with the **exact same schemas** as `processed/` (`etl/contract/DATA_CONTRACT.md`). Use `fixtures/` for fast unit tests, CI checks, and UI state testing, and point production builds at `processed/`.

---

## 1. Files in `fixtures/`

| File | Rows / Lines | Purpose |
|---|---:|---|
| `runs.csv` | `28` | Sample runs across all 6 sources (`PSI-69`, `PSI-25`, `PSI-107`, `PSI-101`, `PSI-102`, `PSI-98`) covering clean rows, duplicate pairs, every QA flag, and every `missing_reason` code. |
| `run_measurements.csv` | `254` | All long-format measurements belonging to the `28` fixture runs (`0` orphan `run_id`s). |
| `corpus_chunks.jsonl` | `15` | `5` chunks per source across PDF, DOCX, PPTX, legacy DOC, and ISA-Tab metadata files. |
| `coverage.csv` | `33` | Full parameter coverage & research-gap matrix (`24` covered cells `COV-01`..`COV-24` + `9` explicit gaps `GAP-25`..`GAP-33`). |
| `issues.csv` | `31` | Full data quality & science-decision log across all 6 investigations. |
| `_meta.json` | — | Counts, timestamps, and edge-case manifest (`"is_fixture": true`). |

---

## 2. Included Fixture Runs (`fixtures/runs.csv`)

| `run_id` | Source | Fuel | `dup_status` (`dup_of`) | `o2_vol_pct` | `pressure_kpa` | `flow_cm_s` | `qa_flags` | Edge Case Tested |
|---|---|---|---|---:|---:|---:|---|---|
| `PSI-69:FLEX-007` | `PSI-69` | `heptane` | unique | 21 | 101.498 | NULL (`unavailable_in_source`) | `*(none)*` | Clean baseline run |
| `PSI-69:FLEX-019` | `PSI-69` | `heptane` | unique | 34 | 71.8739 | NULL (`unavailable_in_source`) | `*(none)*` | Sub-atm enriched-O₂ exploration regime (`COV-07`) |
| `PSI-69:FLEX-114` | `PSI-69` | `methanol` | unique | 20 | NULL (`invalid_value`) | NULL (`unavailable_in_source`) | `impossible_value_nulled` | Impossible pressure (`0 mmHg`) nulled |
| `PSI-69:FLEX-070` | `PSI-69` | `heptane` | unique | 15 | 101.458 | NULL (`unavailable_in_source`) | `identifier_reused` | Shared `FLEX Identifier = 193F001` |
| `PSI-69:FLEX-073` | `PSI-69` | `heptane` | unique | 15 | 101.458 | NULL (`unavailable_in_source`) | `identifier_reused` | Shared `FLEX Identifier = 193F001` |
| `PSI-69:FLEX-069` | `PSI-69` | `heptane` | unique | 14 | 102.271 | NULL (`unavailable_in_source`) | `gas_sum_off` | Gas mole fractions sum to `0.98` |
| `PSI-25:B1` | `PSI-25` | `PMMA` | unique | 22.2 | NULL (`unavailable_in_source`) | NULL (`pending_review`) | `fuel_label_normalised` | Single-number `Air display` awaiting calibration sign-off |
| `PSI-25:B4` | `PSI-25` | `PMMA` | unique | 22.2 | NULL (`unavailable_in_source`) | NULL (`pending_review`) | `negative_gas_reading;fuel_label_normalised` | Negative sensor offset (`CO = -1 ppm`) |
| `PSI-25:O20` | `PSI-25` | `PMMA` | unique | 16.5 | NULL (`unavailable_in_source`) | NULL (`not_parseable`) | `date_year_typo_in_source;negative_gas_reading;fuel_label_normalised` | Negative sensor offset (`CO = -1 ppm`) |
| `PSI-25:T1` | `PSI-25` | `SIBAL` | unique | 18.5 | NULL (`unavailable_in_source`) | NULL (`pending_review`) | `fuel_label_normalised` | Single-number `Air display` awaiting calibration sign-off |
| `PSI-25:F1` | `PSI-25` | `Nomex` | unique | 22.2 | NULL (`unavailable_in_source`) | NULL (`pending_review`) | `fuel_label_normalised` | Single-number `Air display` awaiting calibration sign-off |
| `PSI-25:F4` | `PSI-25` | `wax candle` | unique | 17.4 | NULL (`unavailable_in_source`) | NULL (`not_parseable`) | `fuel_label_normalised` | Clean baseline run |
| `PSI-107:D45-143708-R001` | `PSI-107` | `ethylene` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 36.39 | `*(none)*` | Clean baseline run |
| `PSI-107:D45-143708-R002` | `PSI-107` | `ethylene` | exact_duplicate (`PSI-107:D45-143708-R001`) | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 36.39 | `*(none)*` | Exact duplicate child row |
| `PSI-107:D45-145007-R003` | `PSI-107` | `ethylene` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 40.15 | `*(none)*` | Clean baseline run |
| `PSI-107:D45-145007-R004` | `PSI-107` | `ethylene` | near_duplicate (`PSI-107:D45-145007-R003`) | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 40.15 | `*(none)*` | Near duplicate child row (within 2%) |
| `PSI-107:D136-165219-R295` | `PSI-107` | `75% propylene` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | -0.28 | `below_physical_range;fuel_label_normalised` | Negative anemometer intercept (`-5.92` / `-0.28 cm/s`) |
| `PSI-107:D48-144358-R030` | `PSI-107` | `ethylene` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | NULL (`not_reported`) | `*(none)*` | Unreported airflow (`not_reported`) |
| `PSI-101:Kapton_51` | `PSI-101` | `Kapton` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 8.1 | `*(none)*` | Clean baseline run |
| `PSI-101:Kapton_51a` | `PSI-101` | `Kapton` | unique (`PSI-101:Kapton_51`) | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 8.1 | `secondary_aging_remeasurement` | Clean baseline run |
| `PSI-101:Kapton_112` | `PSI-101` | `Kapton` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 2 | `added_from_workbook` | Clean baseline run |
| `PSI-101:GNDVERIF_1` | `PSI-101` | `Teflon` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 8.1 | `*(none)*` | Clean baseline run |
| `PSI-102:FLIGHT_1` | `PSI-102` | `Silicone` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 8.1 | `outside_documented_hardware_range` | Clean baseline run |
| `PSI-102:GROUND_23S` | `PSI-102` | `Silicone` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 8 | `*(none)*` | Clean baseline run |
| `PSI-102:TABLE_4` | `PSI-102` | `Teflon` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | 10 | `outside_documented_hardware_range` | Clean baseline run |
| `PSI-102:TABLE_5` | `PSI-102` | `Kapton` | unique | NULL (`unavailable_in_source`) | NULL (`unavailable_in_source`) | NULL (`not_reported`) | `*(none)*` | Unreported airflow (`not_reported`) |
| `PSI-98:S1` | `PSI-98` | `SIBAL fabric (75% cotton / 25% fiberglass)` | unique | 21.6 | NULL (`unavailable_in_source`) | 20 | `dimensions_swapped_in_source;suspect_thickness_unit` | Clean baseline run |
| `PSI-98:S2` | `PSI-98` | `SIBAL fabric (75% cotton / 25% fiberglass)` | unique | 21.5 | NULL (`unavailable_in_source`) | 20 | `dimensions_swapped_in_source;suspect_thickness_unit` | Clean baseline run |

---

## 3. Role-by-Role Handoff Guide

- **Zeiad (Backend / API):** Load `fixtures/*.csv` in automated tests to verify that your API filters (`dup_status == 'unique'` by default), null handlers (`missing_reason` badges), and join keys (`runs.run_id == run_measurements.run_id`) handle every edge case without crashing.
- **Malak (Science / Physics):** Inspect the flagged rows in `fixtures/runs.csv` alongside `docs/DATA_DICTIONARY.md` and `docs/QA_REPORT.md` to confirm the 9 open science decisions (`I-001`, `I-006`, `I-007`, `I-008`, `I-016`, `I-024`, `I-025`, `I-028`, `I-031`).
- **Karim (AI / RAG Chatbot):** Use `fixtures/corpus_chunks.jsonl` (`15` chunks across the document archive) for fast embedding/citation smoke tests, and `processed/corpus_chunks.jsonl` (`1,312` chunks) for the full vector index.
- **Farah Khafagy (Frontend / UI):** Use `fixtures/` to preview every UI badge state: `unique` vs `exact_duplicate` vs `near_duplicate`, `qa_flags` pills, `missing_reason` tooltips (`unavailable_in_source`, `pending_review`, `not_parseable`, `invalid_value`, `not_reported`), and the `coverage.csv` research-gap cells (`GAP-25`–`GAP-33`).
