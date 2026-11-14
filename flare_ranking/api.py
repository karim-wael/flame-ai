"""
api.py - FastAPI wrapper. Run from the flare_ranking folder:

    set FLARE_DATA_DIR=C:\\path\\to\\FLARE_AI_Data_Handoff        (Windows)
    py -m uvicorn api:app --reload

Then open http://127.0.0.1:8000/docs -> POST /api/compare -> Try it out.
Zeiad: merge this into your own backend as you like; the logic is in compare_service.py.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from compare_service import compare, load_table

STATE = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    STATE["table"], STATE["issues"] = load_table()   # loaded once, not per request
    yield


app = FastAPI(title="FLARE AI ranking", lifespan=lifespan)


class CompareRequest(BaseModel):
    domain: str
    gravity: str | None = None            # "microgravity" | "normal_gravity" | omitted
    o2_percent: float | None = None
    pressure_psi: float | None = None
    airflow_cm_s: float | None = None
    weights: dict[str, float] | None = None
    top_k: int | None = 10
    min_coverage: float = 0.5


@app.get("/api/health")
def health():
    return {"status": "ok", "ranked_rows": len(STATE["table"])}


@app.post("/api/compare")
def compare_endpoint(req: CompareRequest):
    try:
        return compare(STATE["table"], req.model_dump())
    except ValueError as e:                # bad domain, bad gravity, no conditions...
        raise HTTPException(status_code=422, detail=str(e))