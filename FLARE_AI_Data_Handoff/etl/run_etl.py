"""Run the full ETL: verify raw -> parse each source -> duplicates -> validate -> write processed/.

Usage (from the HACKATHON folder):  python -m etl.run_etl
"""
import csv
import json
import sys
from collections import Counter
from datetime import datetime, timezone

from etl.adapters import bass2, flex, spice
from etl.adapters.salma_sources import saffire1, same, samer
from etl.core.build_corpus import build_corpus
from etl.core.build_fixtures import build_fixtures
from etl.core.common import (CONTRACT_VERSION, ETL_VERSION, MEAS_FIELDS, ROOT, RUN_FIELDS,
                             mark_duplicates, validate, verify_raw)
from etl.core.coverage_and_qa import build_coverage_and_qa

OUT = ROOT / "processed"
ADAPTERS = [flex, bass2, spice, samer, same, saffire1]


def write_csv(path, fields, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def main() -> int:
    problems = verify_raw()
    if problems:
        print("RAW VERIFY FAILED:\n  " + "\n  ".join(problems))
        return 1
    print("Raw archive verified.")

    runs, parsed_counts = [], {}
    for a in ADAPTERS:
        got = a.parse()
        parsed_counts[a.SOURCE_ID] = len(got)
        runs += got
        print(f"  {a.SOURCE_ID}: parsed {len(got)} rows")

    mark_duplicates(runs)
    kept, rejected = validate(runs)
    for r in kept:
        r.data["qa_flags"] = ";".join(r.flags)

    OUT.mkdir(exist_ok=True)
    runs_rows = [r.data for r in kept]
    meas_rows = [m for r in kept for m in r.measurements]
    write_csv(OUT / "runs.csv", RUN_FIELDS, runs_rows)
    write_csv(OUT / "run_measurements.csv", MEAS_FIELDS, meas_rows)
    write_csv(OUT / "rejected.csv", ["run_id", "source_id", "source_row", "reasons"], rejected)
    build_coverage_and_qa(runs_rows, meas_rows, rejected)
    corpus_meta = build_corpus()
    fixtures_meta = build_fixtures(runs_rows, meas_rows)

    summary = {}
    for sid in parsed_counts:
        rs = [r.data for r in kept if r.data["source_id"] == sid]
        summary[sid] = {
            "parsed": parsed_counts[sid],
            "kept": len(rs),
            "rejected": sum(1 for x in rejected if x["source_id"] == sid),
            "dup_status": dict(Counter(x["dup_status"] for x in rs)),
            "has_o2": sum(1 for x in rs if x["o2_vol_pct"] != ""),
            "has_pressure": sum(1 for x in rs if x["pressure_kpa"] != ""),
            "has_flow": sum(1 for x in rs if x["flow_cm_s"] != ""),
            "qa_flags": dict(Counter(f for r in kept if r.data["source_id"] == sid for f in r.flags)),
        }
    meta = {
        "contract_version": CONTRACT_VERSION, "etl_version": ETL_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "runs": len(kept), "measurements": sum(len(r.measurements) for r in kept),
        "rejected": len(rejected), "corpus": corpus_meta,
        "fixtures": {
            "runs": fixtures_meta["runs"],
            "measurements": fixtures_meta["measurements"],
            "corpus_chunks": fixtures_meta["corpus_chunks"],
        },
        "by_source": summary,
    }
    (OUT / "_meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
