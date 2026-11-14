"""Needs: pip install -r requirements-api.txt. Skipped automatically if fastapi is missing."""
import os
import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient   # noqa: E402

DATA = os.environ.get("FLARE_DATA_DIR")
pytestmark = pytest.mark.skipif(not DATA, reason="set FLARE_DATA_DIR to run the API tests")


def client():
    from api import app
    return TestClient(app)


def test_compare_ok_and_errors():
    with client() as c:
        ok = c.post("/api/compare", json={"domain": "liquid_droplet", "o2_percent": 21, "pressure_psi": 14.7})
        assert ok.status_code == 200 and ok.json()["results"]
        assert c.post("/api/compare", json={"domain": "plasma", "o2_percent": 21}).status_code == 422
        assert c.post("/api/compare", json={"domain": "solid", "o2_percent": 21, "gravity": "partial_gravity"}).status_code == 422
        assert c.get("/api/health").json()["status"] == "ok"