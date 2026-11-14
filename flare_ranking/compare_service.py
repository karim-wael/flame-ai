"""
compare_service.py - the logic behind POST /api/compare, with NO web framework
needed (so it can be tested anywhere). api.py is a thin FastAPI wrapper around it.
"""
from __future__ import annotations

import os
from pathlib import Path

import pandas as pd

from adapter import build_ranking_table
from ranking import rank_experiments


def load_table(data_dir: str | os.PathLike | None = None):
    """
    Load the real ranking table once (call this at server start-up).
    data_dir = the unzipped FLARE_AI_Data_Handoff folder (has processed/ and data/).
    Falls back to the FLARE_DATA_DIR environment variable.
    """
    data_dir = data_dir or os.environ.get("FLARE_DATA_DIR")
    if not data_dir:
        raise RuntimeError("Set FLARE_DATA_DIR to the unzipped FLARE_AI_Data_Handoff folder.")
    root = Path(data_dir)
    runs = pd.read_csv(root / "processed" / "runs.csv")
    registry = pd.read_csv(root / "data" / "source_registry.csv")
    table, issues = build_ranking_table(runs, registry)
    return table, issues


def compare(table: pd.DataFrame, body: dict) -> dict:
    """
    body = {"domain": ..., "gravity": optional, "o2_percent": optional,
            "pressure_psi": optional, "airflow_cm_s": optional,
            "weights": optional dict, "top_k": optional int, "min_coverage": optional float}
    Returns the ranking response. Raises ValueError for bad input (-> HTTP 422).
    """
    body = dict(body)
    weights = body.pop("weights", None)
    top_k = body.pop("top_k", 10)
    min_coverage = body.pop("min_coverage", 0.5)
    query = {k: v for k, v in body.items() if v is not None}
    return rank_experiments(table, query, weights=weights, top_k=top_k, min_coverage=min_coverage)