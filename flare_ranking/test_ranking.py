import json

import numpy as np
import pandas as pd
import pytest

from mock_data import load_mock_experiments
from ranking import rank_experiments

QUERY = {"domain": "gas_jet", "o2_percent": 21, "pressure_psi": 14.7, "airflow_cm_s": 10}


@pytest.fixture
def df():
    return load_mock_experiments()


def ids(result):
    return [r["experiment_id"] for r in result["results"]]


def test_exact_match_ranks_first_with_perfect_score(df):
    res = rank_experiments(df, QUERY)
    assert ids(res)[0] == "MOCK-G1"
    assert res["results"][0]["score"] == 1.0


def test_other_domains_are_excluded_not_just_ranked_low(df):
    res = rank_experiments(df, QUERY, top_k=None, min_coverage=0.0)
    assert all(i.startswith("MOCK-G") for i in ids(res))
    assert res["n_excluded_by_domain_or_gravity"] == 6  # 3 solid + 3 liquid


def test_missing_value_is_skipped_not_filled_in(df):
    res = rank_experiments(df, QUERY, top_k=None)
    g4 = next(r for r in res["results"] if r["experiment_id"] == "MOCK-G4")
    assert g4["missing_variables"] == ["airflow_cm_s"]
    assert g4["breakdown"][2]["experiment_value"] is None
    assert g4["coverage"] == pytest.approx(2 / 3, abs=1e-3)
    # perfect on the two variables it has -> similarity 1.0. Filling airflow with 0
    # would have pulled this below 1.0. The score is then scaled by coverage.
    assert g4["similarity"] == 1.0
    assert g4["score"] == pytest.approx(2 / 3, abs=1e-3)
    assert "Not reported" in g4["explanation"]


def test_tie_goes_to_experiment_with_more_data(df):
    res = rank_experiments(df, QUERY)
    assert ids(res).index("MOCK-G1") < ids(res).index("MOCK-G4")


def test_too_little_data_is_dropped_by_default(df):
    assert "MOCK-G6" not in ids(rank_experiments(df, QUERY, top_k=None))
    res = rank_experiments(df, QUERY, top_k=None, min_coverage=0.0)
    assert "MOCK-G6" in ids(res)


def test_weights_change_the_order(df):
    default = ids(rank_experiments(df, QUERY, top_k=None))
    assert default.index("MOCK-G2") < default.index("MOCK-G3")
    airflow_heavy = ids(
        rank_experiments(df, QUERY, weights={"airflow_cm_s": 100}, top_k=None)
    )
    assert airflow_heavy.index("MOCK-G3") < airflow_heavy.index("MOCK-G2")


def test_gravity_filter(df):
    res = rank_experiments(df, {**QUERY, "gravity": "microgravity"}, top_k=None)
    assert "MOCK-G5" not in ids(res)


def test_user_can_select_only_some_variables(df):
    res = rank_experiments(df, {"domain": "gas_jet", "o2_percent": 21}, top_k=None)
    assert set(res["results"][0]["breakdown"][0]) >= {"variable", "closeness"}
    assert len(res["results"][0]["breakdown"]) == 1


def test_top_k_limits_results(df):
    assert len(rank_experiments(df, QUERY, top_k=2)["results"]) == 2


def test_output_is_json_safe_with_no_nan(df):
    res = rank_experiments(df, QUERY, top_k=None, min_coverage=0.0)
    json.dumps(res, allow_nan=False)  # raises if NaN/inf sneaks in


def test_input_table_is_not_modified(df):
    before = df.copy()
    rank_experiments(df, QUERY)
    pd.testing.assert_frame_equal(df, before)


def test_no_divide_by_zero_when_everything_is_equal():
    df = pd.DataFrame(
        {"experiment_id": ["a", "b"], "domain": ["gas_jet", "gas_jet"], "o2_percent": [21.0, 21.0]}
    )
    res = rank_experiments(df, {"domain": "gas_jet", "o2_percent": 21})
    assert [r["score"] for r in res["results"]] == [1.0, 1.0]


def test_empty_pool_returns_empty_results(df):
    res = rank_experiments(df[df["domain"] == "solid"], QUERY)
    assert res["results"] == []


@pytest.mark.parametrize(
    "bad_query",
    [
        {"o2_percent": 21},                                   # no domain
        {"domain": "plasma", "o2_percent": 21},               # unknown domain
        {"domain": "gas_jet"},                                    # no conditions
        {"domain": "gas_jet", "o2_percent": "lots"},              # not a number
        {"domain": "gas_jet", "o2_percent": float("nan")},        # NaN
        {"domain": "gas_jet", "o2_percent": 21, "gravity": "partial_gravity"},
    ],
)
def test_bad_queries_are_rejected(df, bad_query):
    with pytest.raises(ValueError):
        rank_experiments(df, bad_query)


@pytest.mark.parametrize(
    "bad_weights", [{"o2_percent": -1}, {"nonsense": 1}, {"o2_percent": 0, "pressure_psi": 0, "airflow_cm_s": 0}]
)
def test_bad_weights_are_rejected(df, bad_weights):
    with pytest.raises(ValueError):
        rank_experiments(df, QUERY, weights=bad_weights)


def test_missing_column_gives_clear_error(df):
    with pytest.raises(ValueError, match="missing required column"):
        rank_experiments(df.drop(columns=["pressure_psi"]), QUERY)


# ---- behaviour added after Farah El Qady's real data arrived ----------------
def only_flow_table():
    return pd.DataFrame(
        {
            "experiment_id": ["a", "b", "c"],
            "domain": ["gas_jet"] * 3,
            "o2_percent": [np.nan] * 3,
            "airflow_cm_s": [5.0, 10.0, 40.0],
            "o2_missing_reason": ["unavailable_in_source"] * 3,
        }
    )


def test_variable_nobody_in_the_domain_reports_is_left_out_not_penalised():
    res = rank_experiments(only_flow_table(), {"domain": "gas_jet", "o2_percent": 21, "airflow_cm_s": 10})
    assert [r["experiment_id"] for r in res["results"]] == ["b", "a", "c"]
    assert res["query"]["variables_used"] == ["airflow_cm_s"]
    assert res["query"]["not_measured_in_domain"] == ["o2_percent"]
    assert res["results"][0]["coverage"] == 1.0
    assert any("Oxygen" in n and "left out" in n for n in res["notes"])


def test_nothing_measured_returns_empty_result_with_a_note():
    res = rank_experiments(only_flow_table(), {"domain": "gas_jet", "o2_percent": 21})
    assert res["results"] == []
    assert any("nothing could be ranked" in n for n in res["notes"])


def test_notes_explain_what_the_domain_gate_excluded(df):
    res = rank_experiments(df, QUERY)
    assert any("not compared" in n for n in res["notes"])


def test_missing_reason_and_context_are_passed_through():
    t = pd.DataFrame(
        {
            "experiment_id": ["a", "b"],
            "domain": ["solid", "solid"],
            "o2_percent": [21.0, 21.0],
            "airflow_cm_s": [np.nan, 20.0],
            "flow_missing_reason": ["pending_review", None],
            "fuel": ["PMMA", "SIBAL"],
            "investigation": ["BASS-II", "SAFFIRE-I"],
        }
    )
    res = rank_experiments(t, {"domain": "solid", "o2_percent": 21, "airflow_cm_s": 20}, min_coverage=0.0)
    a = next(r for r in res["results"] if r["experiment_id"] == "a")
    assert a["breakdown"][1]["missing_reason"] == "pending_review"
    assert a["context"] == {"investigation": "BASS-II", "fuel": "PMMA"}


def test_partial_match_cannot_outrank_a_fully_compared_similar_experiment():
    t = pd.DataFrame(
        {
            "experiment_id": ["a", "b", "c"],
            "domain": ["solid"] * 3,
            "o2_percent": [21.0, 21.0, 21.0],
            "airflow_cm_s": [np.nan, 10.5, 40.0],
        }
    )
    res = rank_experiments(t, {"domain": "solid", "o2_percent": 21, "airflow_cm_s": 10}, min_coverage=0.0)
    assert [r["experiment_id"] for r in res["results"]] == ["b", "a", "c"]
    a = res["results"][1]
    assert a["similarity"] == 1.0 and a["score"] == pytest.approx(0.5)
    assert "x coverage" in a["explanation"]