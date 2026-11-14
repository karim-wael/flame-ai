"""Stage 6: Build deterministic, edge-case-complete test fixtures in fixtures/.

Generates:
  - fixtures/runs.csv (18 curated runs: 6 per source covering all fuels, QA flags,
    missing_reason codes, exact_duplicate, and near_duplicate pairs)
  - fixtures/run_measurements.csv (all long-format measurements for those 18 runs)
  - fixtures/corpus_chunks.jsonl (15 representative chunks: 5 per source across
    PDF, DOCX, PPTX, legacy DOC, and ISA-Tab metadata)
  - fixtures/coverage.csv (full 26-row coverage & gap matrix)
  - fixtures/issues.csv (full 25-row issues table)
  - fixtures/_meta.json (fixture counts & edge-case manifest)
  - fixtures/README.md (handoff guide for Zeiad, Malak, Karim, and Farah Khafagy)
"""
from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime, timezone

from .common import CONTRACT_VERSION, ETL_VERSION, MEAS_FIELDS, ROOT, RUN_FIELDS


def _select_fixture_runs(runs_rows: list[dict]) -> list[dict]:
    by_id = {r["run_id"]: r for r in runs_rows}
    selected_ids: list[str] = []

    def add(rid: str) -> None:
        if rid in by_id and rid not in selected_ids:
            selected_ids.append(rid)

    # --- PSI-69 (FLEX): 6 runs ---
    # 1. Clean heptane run
    for r in runs_rows:
        if r["source_id"] == "PSI-69" and r["fuel"] == "heptane" and not r["qa_flags"]:
            add(r["run_id"])
            break
    # 2. Sub-atmospheric enriched-O2 exploration habitat run (>23% O2, <85 kPa)
    for r in runs_rows:
        if (
            r["source_id"] == "PSI-69"
            and r["o2_vol_pct"] != ""
            and r["pressure_kpa"] != ""
            and float(r["o2_vol_pct"]) > 23.0
            and float(r["pressure_kpa"]) < 85.0
        ):
            add(r["run_id"])
            break
    # 3. Impossible pressure value nulled (Test 114, 0 mmHg)
    for r in runs_rows:
        if r["source_id"] == "PSI-69" and "impossible_value_nulled" in r["qa_flags"]:
            add(r["run_id"])
            break
    # 4 & 5. Reused FLEX Identifier pair (Tests 183 & 184)
    for r in runs_rows:
        if r["source_id"] == "PSI-69" and "identifier_reused" in r["qa_flags"]:
            add(r["run_id"])
    # 6. Gas sum off (rounding to 0.98)
    for r in runs_rows:
        if r["source_id"] == "PSI-69" and "gas_sum_off" in r["qa_flags"]:
            add(r["run_id"])
            break

    # --- PSI-25 (BASS-II): 6 runs ---
    # 1. PMMA with pending_review numeric Air display
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and r["fuel"] == "PMMA" and r["flow_missing_reason"] == "pending_review":
            add(r["run_id"])
            break
    # 2. PMMA with negative_gas_reading (CO = -1 ppm)
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and "negative_gas_reading" in r["qa_flags"]:
            add(r["run_id"])
            break
    # 3. PMMA with date_year_typo_in_source (2016 / 2018)
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and "date_year_typo_in_source" in r["qa_flags"]:
            add(r["run_id"])
            break
    # 4. SIBAL fabric
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and r["fuel"] == "SIBAL":
            add(r["run_id"])
            break
    # 5. Nomex fabric
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and r["fuel"] == "Nomex":
            add(r["run_id"])
            break
    # 6. Wax candle
    for r in runs_rows:
        if r["source_id"] == "PSI-25" and r["fuel"] == "wax candle":
            add(r["run_id"])
            break

    # --- PSI-107 (SPICE): 6 runs ---
    # 1 & 2. Exact duplicate pair (parent unique + exact_duplicate child)
    for r in runs_rows:
        if r["source_id"] == "PSI-107" and r["dup_status"] == "exact_duplicate" and r["dup_of"]:
            add(r["dup_of"])
            add(r["run_id"])
            break
    # 3 & 4. Near duplicate pair (parent unique + near_duplicate child)
    for r in runs_rows:
        if r["source_id"] == "PSI-107" and r["dup_status"] == "near_duplicate" and r["dup_of"]:
            add(r["dup_of"])
            add(r["run_id"])
            break
    # 5. Negative calibration intercept airflow (below_physical_range, e.g. -5.92 cm/s)
    for r in runs_rows:
        if r["source_id"] == "PSI-107" and "below_physical_range" in r["qa_flags"]:
            add(r["run_id"])
            break
    # 6. Missing airflow (flow_missing_reason == not_reported)
    for r in runs_rows:
        if r["source_id"] == "PSI-107" and r["flow_missing_reason"] == "not_reported":
            add(r["run_id"])
            break

    # --- PSI-101 (SAME-R): 4 runs (matching Salma's fixture selection + workbook-added 112) ---
    for rid in ("PSI-101:Kapton_51", "PSI-101:Kapton_51a", "PSI-101:Kapton_112", "PSI-101:GNDVERIF_1"):
        add(rid)

    # --- PSI-102 (SAME): 4 runs (flight, ground, table 10 cm/s, table blank) ---
    for rid in ("PSI-102:FLIGHT_1", "PSI-102:GROUND_23S", "PSI-102:TABLE_4", "PSI-102:TABLE_5"):
        add(rid)

    # --- PSI-98 (SAFFIRE-I): both large-scale Cygnus burns ---
    for rid in ("PSI-98:S1", "PSI-98:S2"):
        add(rid)

    return [by_id[rid] for rid in selected_ids]


def build_fixtures(runs_rows: list[dict], meas_rows: list[dict]) -> dict:
    proc_dir = ROOT / "processed"
    fix_dir = ROOT / "fixtures"
    fix_dir.mkdir(parents=True, exist_ok=True)

    fix_runs = _select_fixture_runs(runs_rows)
    fix_run_ids = {r["run_id"] for r in fix_runs}
    fix_meas = [m for m in meas_rows if m["run_id"] in fix_run_ids]

    with open(fix_dir / "runs.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=RUN_FIELDS)
        w.writeheader()
        w.writerows(fix_runs)

    with open(fix_dir / "run_measurements.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MEAS_FIELDS)
        w.writeheader()
        w.writerows(fix_meas)

    # Select 15 diverse corpus chunks (5 per source across different documents)
    all_chunks = [
        json.loads(line)
        for line in (proc_dir / "corpus_chunks.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    fix_chunks: list[dict] = []
    for sid in ("PSI-69", "PSI-25", "PSI-107"):
        seen_docs: set[str] = set()
        for ch in all_chunks:
            if ch["source_id"] == sid and ch["doc_file"] not in seen_docs and ch["char_count"] >= 400:
                fix_chunks.append(ch)
                seen_docs.add(ch["doc_file"])
                if len(seen_docs) == 5:
                    break

    with open(fix_dir / "corpus_chunks.jsonl", "w", encoding="utf-8") as f:
        for ch in fix_chunks:
            f.write(json.dumps(ch, ensure_ascii=False) + "\n")

    shutil.copyfile(proc_dir / "coverage.csv", fix_dir / "coverage.csv")
    shutil.copyfile(proc_dir / "issues.csv", fix_dir / "issues.csv")

    fix_meta = {
        "is_fixture": True,
        "contract_version": CONTRACT_VERSION,
        "etl_version": ETL_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": len(fix_runs),
        "measurements": len(fix_meas),
        "corpus_chunks": len(fix_chunks),
        "coverage_rows": sum(1 for _ in open(fix_dir / "coverage.csv", encoding="utf-8")) - 1,
        "issues_rows": sum(1 for _ in open(fix_dir / "issues.csv", encoding="utf-8")) - 1,
        "run_ids_by_source": {
            sid: [r["run_id"] for r in fix_runs if r["source_id"] == sid]
            for sid in ("PSI-69", "PSI-25", "PSI-107", "PSI-101", "PSI-102", "PSI-98")
        },
        "edge_cases_covered": [
            "clean_unique_runs (all 6 sources)",
            "exploration_habitat_sub_atm_enriched_o2 (PSI-69)",
            "impossible_value_nulled (PSI-69 Test 114, 0 mmHg -> NULL + invalid_value)",
            "identifier_reused (PSI-69 Tests 183 & 184 sharing 193F001)",
            "gas_sum_off (PSI-69 rounding sum 0.98)",
            "pending_review_fan_calibration (PSI-25 numeric Air display)",
            "negative_gas_reading (PSI-25 Initial CO = -1 ppm)",
            "date_year_typo_in_source (PSI-25 2016/2018 year typo)",
            "exact_duplicate_pair_with_dup_of (PSI-107)",
            "near_duplicate_pair_with_dup_of (PSI-107)",
            "below_physical_range_negative_cal_intercept (PSI-107 Air Rate = -5.92 / -0.28 cm/s)",
            "not_reported_missing_airflow (PSI-107 & PSI-102 blank airflow)",
            "secondary_aging_remeasurement_with_parent_dup_of (PSI-101:Kapton_51a -> PSI-101:Kapton_51)",
            "added_from_workbook (PSI-101:Kapton_112)",
            "normal_gravity_1g_ground_baselines (PSI-101:GNDVERIF_1 & PSI-102:GROUND_23S)",
            "outside_documented_hardware_range (PSI-102:TABLE_4 at 10 cm/s)",
            "cygnus_large_scale_burns_and_swapped_dimensions (PSI-98:S1 & PSI-98:S2)",
        ],
    }
    (fix_dir / "_meta.json").write_text(json.dumps(fix_meta, indent=2), encoding="utf-8")

    _write_fixtures_readme(
        fix_dir / "README.md",
        fix_runs,
        fix_meas,
        fix_chunks,
        fix_meta["coverage_rows"],
        fix_meta["issues_rows"],
    )
    return fix_meta


def _write_fixtures_readme(
    path: Path,
    fix_runs: list[dict],
    fix_meas: list[dict],
    fix_chunks: list[dict],
    cov_count: int,
    iss_count: int,
) -> None:
    lines = [
        "# FLARE AI — Test Fixtures (`fixtures/`)",
        "",
        "**Owners:** Data Engineering (Farah El Qady, Salma)  ",
        f"**Contract Version:** `{CONTRACT_VERSION}` · **ETL Version:** `{ETL_VERSION}`",
        "",
        "This folder contains lightweight, deterministic sample files with the **exact same schemas** as `processed/` (`etl/contract/DATA_CONTRACT.md`). Use `fixtures/` for fast unit tests, CI checks, and UI state testing, and point production builds at `processed/`.",
        "",
        "---",
        "",
        "## 1. Files in `fixtures/`",
        "",
        "| File | Rows / Lines | Purpose |",
        "|---|---:|---|",
        f"| `runs.csv` | `{len(fix_runs)}` | Sample runs across all 6 sources (`PSI-69`, `PSI-25`, `PSI-107`, `PSI-101`, `PSI-102`, `PSI-98`) covering clean rows, duplicate pairs, every QA flag, and every `missing_reason` code. |",
        f"| `run_measurements.csv` | `{len(fix_meas)}` | All long-format measurements belonging to the `{len(fix_runs)}` fixture runs (`0` orphan `run_id`s). |",
        f"| `corpus_chunks.jsonl` | `{len(fix_chunks)}` | `5` chunks per source across PDF, DOCX, PPTX, legacy DOC, and ISA-Tab metadata files. |",
        f"| `coverage.csv` | `{cov_count}` | Full parameter coverage & research-gap matrix (`24` covered cells `COV-01`..`COV-24` + `9` explicit gaps `GAP-25`..`GAP-33`). |",
        f"| `issues.csv` | `{iss_count}` | Full data quality & science-decision log across all 6 investigations. |",
        "| `_meta.json` | — | Counts, timestamps, and edge-case manifest (`\"is_fixture\": true`). |",
        "",
        "---",
        "",
        "## 2. Included Fixture Runs (`fixtures/runs.csv`)",
        "",
        "| `run_id` | Source | Fuel | `dup_status` (`dup_of`) | `o2_vol_pct` | `pressure_kpa` | `flow_cm_s` | `qa_flags` | Edge Case Tested |",
        "|---|---|---|---|---:|---:|---:|---|---|",
    ]
    for r in fix_runs:
        dup_str = r["dup_status"] + (f" (`{r['dup_of']}`)" if r["dup_of"] else "")
        o2_str = r["o2_vol_pct"] if r["o2_vol_pct"] != "" else f"NULL (`{r['o2_missing_reason']}`)"
        p_str = r["pressure_kpa"] if r["pressure_kpa"] != "" else f"NULL (`{r['pressure_missing_reason']}`)"
        fl_str = r["flow_cm_s"] if r["flow_cm_s"] != "" else f"NULL (`{r['flow_missing_reason']}`)"
        flags = r["qa_flags"] or "*(none)*"
        edge = "Clean baseline run"
        if "impossible_value_nulled" in r["qa_flags"]:
            edge = "Impossible pressure (`0 mmHg`) nulled"
        elif "identifier_reused" in r["qa_flags"]:
            edge = "Shared `FLEX Identifier = 193F001`"
        elif "gas_sum_off" in r["qa_flags"]:
            edge = "Gas mole fractions sum to `0.98`"
        elif r["source_id"] == "PSI-69" and r["pressure_kpa"] and float(r["pressure_kpa"]) < 85:
            edge = "Sub-atm enriched-O₂ exploration regime (`COV-07`)"
        elif "negative_gas_reading" in r["qa_flags"]:
            edge = "Negative sensor offset (`CO = -1 ppm`)"
        elif "date_year_typo_in_source" in r["qa_flags"]:
            edge = "Source year typo (`2016`/`2018` vs `GMT` 2014)"
        elif r["flow_missing_reason"] == "pending_review":
            edge = "Single-number `Air display` awaiting calibration sign-off"
        elif r["dup_status"] == "exact_duplicate":
            edge = "Exact duplicate child row"
        elif r["dup_status"] == "near_duplicate":
            edge = "Near duplicate child row (within 2%)"
        elif "below_physical_range" in r["qa_flags"]:
            edge = "Negative anemometer intercept (`-5.92` / `-0.28 cm/s`)"
        elif r["flow_missing_reason"] == "not_reported":
            edge = "Unreported airflow (`not_reported`)"
        lines.append(
            f"| `{r['run_id']}` | `{r['source_id']}` | `{r['fuel']}` | {dup_str} | {o2_str} | {p_str} | {fl_str} | `{flags}` | {edge} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 3. Role-by-Role Handoff Guide",
        "",
        "- **Zeiad (Backend / API):** Load `fixtures/*.csv` in automated tests to verify that your API filters (`dup_status == 'unique'` by default), null handlers (`missing_reason` badges), and join keys (`runs.run_id == run_measurements.run_id`) handle every edge case without crashing.",
        "- **Malak (Science / Physics):** Inspect the flagged rows in `fixtures/runs.csv` alongside `docs/DATA_DICTIONARY.md` and `docs/QA_REPORT.md` to confirm the 9 open science decisions (`I-001`, `I-006`, `I-007`, `I-008`, `I-016`, `I-024`, `I-025`, `I-028`, `I-031`).",
        "- **Karim (AI / RAG Chatbot):** Use `fixtures/corpus_chunks.jsonl` (`15` chunks across the document archive) for fast embedding/citation smoke tests, and `processed/corpus_chunks.jsonl` (`1,312` chunks) for the full vector index.",
        "- **Farah Khafagy (Frontend / UI):** Use `fixtures/` to preview every UI badge state: `unique` vs `exact_duplicate` vs `near_duplicate`, `qa_flags` pills, `missing_reason` tooltips (`unavailable_in_source`, `pending_review`, `not_parseable`, `invalid_value`, `not_reported`), and the `coverage.csv` research-gap cells (`GAP-25`–`GAP-33`).",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
