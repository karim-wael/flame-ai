import json
import pytest
from mock_data import load_mock_experiments
from compare_service import compare

BODY = {"domain": "gas_jet", "o2_percent": 21, "pressure_psi": 14.7, "airflow_cm_s": 10}


def test_returns_ranking_and_is_json_safe():
    res = compare(load_mock_experiments(), BODY)
    assert res["results"][0]["experiment_id"] == "MOCK-G1"
    json.dumps(res, allow_nan=False)


def test_none_fields_are_ignored_and_options_are_used():
    body = {**BODY, "gravity": None, "weights": None, "top_k": 2, "min_coverage": 0.5}
    assert len(compare(load_mock_experiments(), body)["results"]) == 2


@pytest.mark.parametrize("bad", [
    {"domain": "plasma", "o2_percent": 21},
    {"domain": "gas_jet", "o2_percent": 21, "gravity": "partial_gravity"},
    {"domain": "gas_jet"},
])
def test_bad_input_raises_value_error(bad):
    with pytest.raises(ValueError):
        compare(load_mock_experiments(), bad)