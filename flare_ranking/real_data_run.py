"""
Run the ranking on Farah El Qady's real data (Data Contract v0.3).

Usage (from the flare_ranking folder):
    py run_on_farah_data.py "C:\\path\\to\\FLARE_AI_Data_Handoff"

The path is the folder that contains `processed/` and `data/` (the unzipped handoff).
"""
import sys
from pathlib import Path

import pandas as pd

from adapter import build_ranking_table
from ranking import rank_experiments

root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
runs = pd.read_csv(root / "processed" / "runs.csv")
registry = pd.read_csv(root / "data" / "source_registry.csv")

table, issues = build_ranking_table(registry=registry, runs=runs)   # default: hide duplicates, negative flow = missing
print(f"Rows in runs.csv: {len(runs)} | ranked: {len(table)} | hidden: {table.attrs['hidden']}")
print("\nData available per domain (how many runs have each variable):")
print(table.groupby("domain")[["o2_percent", "pressure_psi", "airflow_cm_s"]].count().to_string())
print(f"\nIssues found by the adapter: {len(issues)}")
if len(issues):
    print(issues.groupby(["field", "problem"]).size().to_string())

queries = [
    {"domain": "liquid_droplet", "o2_percent": 21, "pressure_psi": 14.7},
    {"domain": "solid", "o2_percent": 21, "airflow_cm_s": 20},
    {"domain": "gas_jet", "airflow_cm_s": 10},
    {"domain": "smoke", "gravity": "microgravity", "airflow_cm_s": 8},
]
for q in queries:
    res = rank_experiments(table, q, top_k=3)
    print("\n" + "=" * 70 + f"\nQUERY: {q}")
    for note in res["notes"]:
        print("  NOTE:", note)
    for r in res["results"]:
        print(f"  #{r['rank']} {r['experiment_id']}  score={r['score']:.3f}  fuel={r['context'].get('fuel')}")
        print("     ", r["explanation"])