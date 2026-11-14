import numpy as np
import pandas as pd
import pytest

from adapter import build_ranking_table
from ranking import rank_experiments


def runs(rows=None, **overrides):
    """A tiny table in Data Contract v0.3 shape."""
    base = {
        "run_id": "PSI-69:T1", "source_id": "PSI-69", "investigation": "FLEX",
        "domain": "liquid_droplet", "gravity_regime": "microgravity", "platform": "ISS",
        "fuel": "heptane", "o2_vol_pct": 21.0, "o2_missing_reason": None,
        "pressure_kpa": 101.325, "pressure_missing_reason": None,
        "flow_cm_s": np.nan, "flow_missing_reason": "unavailable_in_source",
        "dup_status": "unique", "qa_flags": "",
    }
    rows = rows or [{}]
    return pd.DataFrame([{**base, **overrides, **r} for r in rows])


REGISTRY = pd.DataFrame({"source_id": ["PSI-69"], "doi": ["10.60555/mbq8-0451"]})


def test_columns_units_and_source_link():
    table, issues = build_ranking_table(runs(), REGISTRY)
    row = table.iloc[0]
    assert row["experiment_id"] == "PSI-69:T1"
    assert row["gravity_level"] == "microgravity"
    assert row["o2_percent"] == 21.0
    assert row["pressure_psi"] == pytest.approx(14.696, abs=0.001)
    assert np.isnan(row["airflow_cm_s"])
    assert row["source_url"] == "https://doi.org/10.60555/mbq8-0451"
    assert row["flow_missing_reason"] == "unavailable_in_source"
    assert issues.empty


def test_duplicates_and_secondary_aging_are_hidden_by_default():
    df = runs([
        {"run_id": "a"},
        {"run_id": "b", "dup_status": "exact_duplicate"},
        {"run_id": "c", "dup_status": "near_duplicate"},
        {"run_id": "d", "qa_flags": "secondary_aging_remeasurement"},
    ])
    table, _ = build_ranking_table(df)
    assert list(table["experiment_id"]) == ["a"]
    assert table.attrs["hidden"] == {"duplicates": 2, "secondary_aging": 1, "unknown_gravity": 0}
    table, _ = build_ranking_table(df, include_duplicates=True, include_secondary_aging=True)
    assert len(table) == 4


@pytest.mark.parametrize("mode, expected", [("missing", None), ("clamp", 0.0), ("keep", -5.92)])
def test_negative_flow_is_a_science_decision(mode, expected):
    table, issues = build_ranking_table(runs(flow_cm_s=-5.92, flow_missing_reason=None), negative_flow=mode)
    value = table.iloc[0]["airflow_cm_s"]
    if expected is None:
        assert np.isnan(value)
        assert table.iloc[0]["flow_missing_reason"] == "invalid_value"
    else:
        assert value == expected
    assert "I-016" in issues.iloc[0]["problem"]


def test_zero_flow_is_a_real_value():
    table, issues = build_ranking_table(runs(flow_cm_s=0.0, flow_missing_reason=None))
    assert table.iloc[0]["airflow_cm_s"] == 0.0
    assert issues.empty


def test_impossible_values_become_missing_and_are_reported():
    table, issues = build_ranking_table(runs(o2_vol_pct=150.0, pressure_kpa=-3.0))
    row = table.iloc[0]
    assert np.isnan(row["o2_percent"]) and np.isnan(row["pressure_psi"])
    assert row["o2_missing_reason"] == "invalid_value"
    assert row["pressure_missing_reason"] == "invalid_value"
    assert set(issues["field"]) == {"o2_vol_pct", "pressure_kpa"}


def test_text_in_a_number_column_is_reported():
    table, issues = build_ranking_table(runs(o2_vol_pct="n/a"))
    assert np.isnan(table.iloc[0]["o2_percent"])
    assert "not a number" in issues.iloc[0]["problem"]


def test_unknown_domain_is_reported():
    _, issues = build_ranking_table(runs(domain="mixed"))
    assert "domain gate" in issues.iloc[0]["problem"]


def test_duplicate_run_ids_are_reported():
    _, issues = build_ranking_table(runs([{}, {}]), include_duplicates=True)
    assert (issues["problem"] == "duplicate run_id").sum() == 2


def test_missing_required_column():
    with pytest.raises(ValueError, match="missing required column"):
        build_ranking_table(runs().drop(columns=["flow_cm_s"]))


def test_bad_negative_flow_mode():
    with pytest.raises(ValueError):
        build_ranking_table(runs(), negative_flow="guess")


def test_end_to_end_into_ranking():
    df = runs([
        {"run_id": "PSI-69:a", "o2_vol_pct": 21.0, "pressure_kpa": 101.325},
        {"run_id": "PSI-69:b", "o2_vol_pct": 30.0, "pressure_kpa": 70.0},
        {"run_id": "PSI-107:c", "domain": "gas_jet", "o2_vol_pct": np.nan, "flow_cm_s": 10.0},
        {"run_id": "PSI-69:d", "dup_status": "exact_duplicate"},
    ])
    table, _ = build_ranking_table(df, REGISTRY)
    res = rank_experiments(table, {"domain": "liquid_droplet", "o2_percent": 21, "pressure_psi": 14.7})
    assert [r["experiment_id"] for r in res["results"]] == ["PSI-69:a", "PSI-69:b"]
    assert res["results"][0]["context"]["fuel"] == "heptane"
    assert res["results"][0]["source_link"].startswith("https://doi.org/")


def test_unknown_gravity_rows_are_hidden_by_default_but_can_be_included():
    df = runs([{"run_id": "a"}, {"run_id": "b", "gravity_regime": "unknown"}])
    table, _ = build_ranking_table(df)
    assert list(table["experiment_id"]) == ["a"]
    assert table.attrs["hidden"]["unknown_gravity"] == 1
    table, _ = build_ranking_table(df, include_unknown_gravity=True)
    assert set(table["experiment_id"]) == {"a", "b"}


def test_blank_missing_reason_columns_do_not_break_flagging():
    df = runs(o2_vol_pct=150.0, o2_missing_reason=np.nan)   # whole column blank -> float dtype
    table, issues = build_ranking_table(df)
    assert table.iloc[0]["o2_missing_reason"] == "invalid_value"