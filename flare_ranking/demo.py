"""Run `python demo.py` to see the ranking on fake data."""
import json

from mock_data import load_mock_experiments
from ranking import rank_experiments

experiments = load_mock_experiments()

query = {
    "domain": "gas_jet",
    "gravity": "microgravity",
    "o2_percent": 21,
    "pressure_psi": 14.7,
    "airflow_cm_s": 10,
}

result = rank_experiments(experiments, query, top_k=5)

print("Selected:", result["query"]["conditions"], "| domain:", result["query"]["domain"])
print(f"Candidates: {result['n_candidates']}, "
      f"excluded (other domain/gravity): {result['n_excluded_by_domain_or_gravity']}, "
      f"dropped (too little data): {result['n_dropped_insufficient_data']}\n")

for r in result["results"]:
    print(f"#{r['rank']}  {r['experiment_id']}  score={r['score']:.3f}  coverage={r['coverage']:.2f}")
    print("    ", r["explanation"])

print("\n", result["disclaimer"])

# This is the JSON the backend would send to the dashboard:
# print(json.dumps(result, indent=2))