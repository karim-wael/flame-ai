from contextlib import asynccontextmanager
import re
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from .config import (
    COMBUSTION_DOMAINS,
    GRAVITY_REGIMES,
    MISSING_REASONS,
    SCIENTIFIC_DISCLAIMER,
    VALUE_STATUSES,
)
from .ingestion import run_ingestion_pipeline
from .models import (
    DataSource,
    DerivedResult,
    ExperimentRun,
    FieldMapping,
    Investigation,
    KnowledgeChunk,
    KnowledgeDocument,
    Measurement,
    SessionLocal,
    SourceFile,
    get_db,
    init_db,
)
from .rag import run_hybrid_assistant_query, warm_retrieval_index
from .schemas import AssistantQueryRequest, CompareRequest, IngestionJobRequest
from .similarity import run_domain_gated_comparison


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if db.query(ExperimentRun).count() < 100:
            run_ingestion_pipeline(db)
        warm_retrieval_index(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="FLARE AI — Microgravity Combustion & Hybrid Knowledge API",
    description=(
        "NASA Space Apps Challenge 2026 | Flame in Freefall. "
        "Expanded Data Strategy (NASA PSI, JAXA DARTS, FSRI MaP) + Hybrid Knowledge Architecture (PostgreSQL + pgvector + RAG)."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def normalize_double_slashes(request: Request, call_next):
    path = request.scope.get("path", "")
    if "//" in path:
        request.scope["path"] = re.sub(r"/{2,}", "/", path)
    return await call_next(request)


def serialize_run(r: ExperimentRun) -> Dict[str, Any]:
    inv = r.investigation
    return {
        "id": r.id,
        "run_code": r.run_code,
        "investigation_id": r.investigation_id,
        "external_investigation_id": inv.external_id if inv else None,
        "investigation_title": inv.title if inv else None,
        "publisher": inv.source.publisher if (inv and inv.source) else None,
        "doi": inv.doi if inv else None,
        "source_url": inv.source_url if inv else None,
        "combustion_domain": r.combustion_domain,
        "gravity_regime": r.gravity_regime,
        "platform": r.platform,
        "fuel_material": r.fuel_material,
        "fuel_state": r.fuel_state,
        "oxidizer": r.oxidizer,
        "oxygen_fraction": r.oxygen_fraction,
        "oxygen_missing_reason": r.oxygen_missing_reason,
        "pressure_value": r.pressure_value,
        "pressure_unit": r.pressure_unit,
        "pressure_normalized_kpa": r.pressure_normalized_kpa,
        "pressure_missing_reason": r.pressure_missing_reason,
        "flow_velocity_value": r.flow_velocity_value,
        "flow_velocity_unit": r.flow_velocity_unit,
        "flow_velocity_normalized_cm_s": r.flow_velocity_normalized_cm_s,
        "flow_velocity_missing_reason": r.flow_velocity_missing_reason,
        "temperature_value": r.temperature_value,
        "temperature_unit": r.temperature_unit,
        "burner_or_sample_geometry": r.burner_or_sample_geometry,
        "droplet_diameter_mm": r.droplet_diameter_mm,
        "sample_orientation": r.sample_orientation,
        "test_environment": r.test_environment,
        "is_terrestrial_baseline": r.is_terrestrial_baseline,
        "run_metadata": r.run_metadata,
        "measurements": [
            {
                "id": m.id,
                "variable_name": m.variable_name,
                "canonical_field": m.canonical_field,
                "value_numeric": m.value_numeric,
                "value_text": m.value_text,
                "unit": m.unit,
                "normalized_value": m.normalized_value,
                "normalized_unit": m.normalized_unit,
                "value_status": m.value_status,
                "uncertainty": m.uncertainty,
                "measurement_method": m.measurement_method,
                "missing_reason": m.missing_reason,
                "source_file_id": m.source_file_id,
                "notes": m.notes,
            }
            for m in r.measurements
        ],
        "derived_results": [
            {
                "id": dr.id,
                "method_name": dr.method_name,
                "method_version": dr.method_version,
                "result_name": dr.result_name,
                "result_value": dr.result_value,
                "result_unit": dr.result_unit,
                "explanation": dr.explanation,
                "input_measurement_ids": dr.input_measurement_ids,
            }
            for dr in r.derived_results
        ],
    }


@app.get("/")
@app.head("/")
@app.get("/api/health")
def get_health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "service": "FLARE AI Hybrid Backend",
        "version": "2.0.0",
        "scientific_disclaimer": SCIENTIFIC_DISCLAIMER,
        "controlled_vocabularies": {
            "gravity_regimes": GRAVITY_REGIMES,
            "combustion_domains": COMBUSTION_DOMAINS,
            "value_statuses": VALUE_STATUSES,
            "missing_reasons": MISSING_REASONS,
        },
        "counts": {
            "data_sources": db.query(DataSource).count(),
            "investigations": db.query(Investigation).count(),
            "experiment_runs": db.query(ExperimentRun).count(),
            "measurements": db.query(Measurement).count(),
            "source_files": db.query(SourceFile).count(),
            "field_mappings": db.query(FieldMapping).count(),
            "derived_results": db.query(DerivedResult).count(),
            "knowledge_documents": db.query(KnowledgeDocument).count(),
            "knowledge_chunks": db.query(KnowledgeChunk).count(),
        },
    }


@app.get("/api/sources")
def list_sources(db: Session = Depends(get_db)):
    sources = (
        db.query(DataSource)
        .options(selectinload(DataSource.field_mappings), selectinload(DataSource.investigations))
        .all()
    )
    return [
        {
            "id": s.id,
            "publisher": s.publisher,
            "source_name": s.source_name,
            "source_url": s.source_url,
            "license": s.license,
            "access_date": s.access_date,
            "citation_text": s.citation_text,
            "priority": s.priority,
            "domain_track": s.domain_track,
            "investigation_count": len(s.investigations),
            "field_mappings": [
                {
                    "id": fm.id,
                    "source_field": fm.source_field,
                    "canonical_field": fm.canonical_field,
                    "source_unit": fm.source_unit,
                    "canonical_unit": fm.canonical_unit,
                    "transform_description": fm.transform_description,
                    "mapping_version": fm.mapping_version,
                }
                for fm in s.field_mappings
            ],
        }
        for s in sources
    ]


@app.get("/api/investigations")
def list_investigations(
    source: Optional[str] = Query(default=None, description="Filter by publisher or source ID"),
    domain: Optional[str] = Query(default=None, description="Filter by combustion_domain"),
    gravity: Optional[str] = Query(default=None, description="Filter by gravity_regime"),
    priority: Optional[str] = Query(default=None, description="Filter by priority (P0, P1, P2)"),
    search: Optional[str] = Query(default=None, description="Free-text search in title, external_id, or focus"),
    db: Session = Depends(get_db),
):
    q = db.query(Investigation).join(DataSource)
    if source:
        q = q.filter(or_(DataSource.publisher.ilike(f"%{source}%"), DataSource.id == source))
    if domain:
        q = q.filter(Investigation.combustion_domain == domain)
    if gravity:
        q = q.filter(Investigation.gravity_regime == gravity)
    if priority:
        q = q.filter(Investigation.priority == priority)
    if search:
        q = q.filter(
            or_(
                Investigation.title.ilike(f"%{search}%"),
                Investigation.external_id.ilike(f"%{search}%"),
                Investigation.platform.ilike(f"%{search}%"),
            )
        )

    invs = q.options(selectinload(Investigation.source)).all()
    run_counts = dict(
        db.query(ExperimentRun.investigation_id, func.count(ExperimentRun.id))
        .group_by(ExperimentRun.investigation_id)
        .all()
    )
    file_counts = dict(
        db.query(SourceFile.investigation_id, func.count(SourceFile.id))
        .group_by(SourceFile.investigation_id)
        .all()
    )
    return [
        {
            "id": inv.id,
            "external_id": inv.external_id,
            "title": inv.title,
            "publisher": inv.source.publisher if inv.source else "NASA PSI",
            "domain_track": inv.source.domain_track if inv.source else "microgravity_research",
            "doi": inv.doi,
            "version": inv.version,
            "project_type": inv.project_type,
            "platform": inv.platform,
            "gravity_regime": inv.gravity_regime,
            "combustion_domain": inv.combustion_domain,
            "priority": inv.priority,
            "start_date": inv.start_date,
            "end_date": inv.end_date,
            "source_url": inv.source_url,
            "source_metadata": inv.source_metadata,
            "run_count": run_counts.get(inv.id, 0),
            "file_count": file_counts.get(inv.id, 0),
        }
        for inv in invs
    ]


@app.get("/api/investigations/{investigation_id}")
def get_investigation_detail(investigation_id: str, db: Session = Depends(get_db)):
    inv = (
        db.query(Investigation)
        .options(
            selectinload(Investigation.source),
            selectinload(Investigation.source_files),
            selectinload(Investigation.experiment_runs).selectinload(ExperimentRun.measurements),
            selectinload(Investigation.experiment_runs).selectinload(ExperimentRun.derived_results),
        )
        .filter(or_(Investigation.id == investigation_id, Investigation.external_id == investigation_id))
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found")

    return {
        "id": inv.id,
        "external_id": inv.external_id,
        "title": inv.title,
        "publisher": inv.source.publisher if inv.source else "NASA PSI",
        "domain_track": inv.source.domain_track if inv.source else "microgravity_research",
        "license": inv.source.license if inv.source else "",
        "citation_text": inv.source.citation_text if inv.source else "",
        "doi": inv.doi,
        "version": inv.version,
        "project_type": inv.project_type,
        "platform": inv.platform,
        "gravity_regime": inv.gravity_regime,
        "combustion_domain": inv.combustion_domain,
        "priority": inv.priority,
        "start_date": inv.start_date,
        "end_date": inv.end_date,
        "source_url": inv.source_url,
        "source_metadata": inv.source_metadata,
        "source_files": [
            {
                "id": sf.id,
                "file_name": sf.file_name,
                "file_url": sf.file_url,
                "mime_type": sf.mime_type,
                "file_size": sf.file_size,
                "checksum_sha256": sf.checksum_sha256,
                "file_role": sf.file_role,
                "version": sf.version,
                "local_storage_key": sf.local_storage_key,
            }
            for sf in inv.source_files
        ],
        "experiment_runs": [serialize_run(r) for r in inv.experiment_runs],
    }


@app.get("/api/investigations/{investigation_id}/files")
def get_investigation_files(investigation_id: str, db: Session = Depends(get_db)):
    inv = (
        db.query(Investigation)
        .filter(or_(Investigation.id == investigation_id, Investigation.external_id == investigation_id))
        .first()
    )
    if not inv:
        raise HTTPException(status_code=404, detail=f"Investigation '{investigation_id}' not found")
    return [
        {
            "id": sf.id,
            "investigation_id": inv.id,
            "external_investigation_id": inv.external_id,
            "file_name": sf.file_name,
            "file_url": sf.file_url,
            "mime_type": sf.mime_type,
            "file_size": sf.file_size,
            "checksum_sha256": sf.checksum_sha256,
            "file_role": sf.file_role,
            "version": sf.version,
            "local_storage_key": sf.local_storage_key,
        }
        for sf in inv.source_files
    ]


@app.post("/api/ingestion/jobs")
def trigger_ingestion_job(req: IngestionJobRequest, db: Session = Depends(get_db)):
    return run_ingestion_pipeline(db, source_filter=req.source_filter)


@app.get("/api/experiments")
def list_experiments(
    domain: Optional[str] = Query(default=None),
    gravity: Optional[str] = Query(default=None),
    investigation_id: Optional[str] = Query(default=None),
    include_baseline: bool = Query(default=True),
    db: Session = Depends(get_db),
):
    q = db.query(ExperimentRun).join(Investigation)
    if domain:
        q = q.filter(ExperimentRun.combustion_domain == domain)
    if gravity:
        q = q.filter(ExperimentRun.gravity_regime == gravity)
    if investigation_id:
        q = q.filter(or_(Investigation.id == investigation_id, Investigation.external_id == investigation_id))
    if not include_baseline:
        q = q.filter(ExperimentRun.is_terrestrial_baseline == False)  # noqa: E712

    runs = q.options(
        selectinload(ExperimentRun.investigation).selectinload(Investigation.source),
        selectinload(ExperimentRun.measurements),
        selectinload(ExperimentRun.derived_results),
    ).all()
    return [serialize_run(r) for r in runs]


@app.get("/api/experiments/{experiment_id}/measurements")
def get_experiment_measurements(experiment_id: str, db: Session = Depends(get_db)):
    run = (
        db.query(ExperimentRun)
        .filter(or_(ExperimentRun.id == experiment_id, ExperimentRun.run_code == experiment_id))
        .first()
    )
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment run '{experiment_id}' not found")
    return serialize_run(run)


@app.post("/api/compare")
def compare_experiments(req: CompareRequest, db: Session = Depends(get_db)):
    return run_domain_gated_comparison(db, req)


@app.get("/api/provenance/{record_id}")
def get_record_provenance(record_id: str, db: Session = Depends(get_db)):
    # 1. Check ExperimentRun by id or run_code
    run = (
        db.query(ExperimentRun)
        .filter(or_(ExperimentRun.id == record_id, ExperimentRun.run_code == record_id))
        .first()
    )
    if run:
        inv = run.investigation
        src = inv.source if inv else None
        return {
            "record_type": "experiment_run",
            "record_id": run.id,
            "run_code": run.run_code,
            "investigation": {
                "id": inv.id if inv else None,
                "external_id": inv.external_id if inv else None,
                "title": inv.title if inv else None,
                "doi": inv.doi if inv else None,
                "version": inv.version if inv else None,
                "source_url": inv.source_url if inv else None,
                "gravity_regime": inv.gravity_regime if inv else None,
                "combustion_domain": inv.combustion_domain if inv else None,
            },
            "source_publisher": {
                "id": src.id if src else None,
                "publisher": src.publisher if src else None,
                "source_name": src.source_name if src else None,
                "license": src.license if src else None,
                "access_date": src.access_date if src else None,
                "citation_text": src.citation_text if src else None,
                "domain_track": src.domain_track if src else None,
            },
            "source_files": [
                {
                    "id": sf.id,
                    "file_name": sf.file_name,
                    "file_url": sf.file_url,
                    "checksum_sha256": sf.checksum_sha256,
                    "version": sf.version,
                    "local_storage_key": sf.local_storage_key,
                }
                for sf in (inv.source_files if inv else [])
            ],
            "field_mappings_applied": [
                {
                    "source_field": fm.source_field,
                    "canonical_field": fm.canonical_field,
                    "source_unit": fm.source_unit,
                    "canonical_unit": fm.canonical_unit,
                    "transform_description": fm.transform_description,
                    "mapping_version": fm.mapping_version,
                }
                for fm in (src.field_mappings if src else [])
            ],
            "derived_audit_trail": [
                {
                    "id": dr.id,
                    "method_name": dr.method_name,
                    "method_version": dr.method_version,
                    "result_name": dr.result_name,
                    "result_value": dr.result_value,
                    "result_unit": dr.result_unit,
                    "explanation": dr.explanation,
                    "input_measurement_ids": dr.input_measurement_ids,
                }
                for dr in run.derived_results
            ],
        }

    # 2. Check Measurement by id
    meas = db.query(Measurement).filter(Measurement.id == record_id).first()
    if meas:
        run = meas.run
        inv = run.investigation if run else None
        src = inv.source if inv else None
        sf = meas.source_file
        return {
            "record_type": "measurement",
            "record_id": meas.id,
            "variable_name": meas.variable_name,
            "canonical_field": meas.canonical_field,
            "original_value": meas.value_numeric,
            "original_unit": meas.unit,
            "normalized_value": meas.normalized_value,
            "normalized_unit": meas.normalized_unit,
            "value_status": meas.value_status,
            "missing_reason": meas.missing_reason,
            "measurement_method": meas.measurement_method,
            "run_code": run.run_code if run else None,
            "external_investigation_id": inv.external_id if inv else None,
            "doi": inv.doi if inv else None,
            "source_url": inv.source_url if inv else None,
            "publisher": src.publisher if src else None,
            "source_file": {
                "file_name": sf.file_name if sf else None,
                "checksum_sha256": sf.checksum_sha256 if sf else None,
                "version": sf.version if sf else None,
            },
        }

    # 3. Check Investigation by id or external_id
    inv = (
        db.query(Investigation)
        .filter(or_(Investigation.id == record_id, Investigation.external_id == record_id))
        .first()
    )
    if inv:
        src = inv.source
        return {
            "record_type": "investigation",
            "record_id": inv.id,
            "external_id": inv.external_id,
            "title": inv.title,
            "doi": inv.doi,
            "version": inv.version,
            "source_url": inv.source_url,
            "publisher": src.publisher if src else None,
            "license": src.license if src else None,
            "citation_text": src.citation_text if src else None,
            "source_files": [
                {
                    "file_name": sf.file_name,
                    "checksum_sha256": sf.checksum_sha256,
                    "version": sf.version,
                }
                for sf in inv.source_files
            ],
        }

    raise HTTPException(status_code=404, detail=f"Provenance record '{record_id}' not found")


@app.get("/api/knowledge/chunks")
def list_knowledge_chunks(
    domain: Optional[str] = Query(default=None),
    gravity: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    q = db.query(KnowledgeChunk)
    if domain:
        q = q.filter(KnowledgeChunk.combustion_domain == domain)
    if gravity:
        q = q.filter(KnowledgeChunk.gravity_regime == gravity)
    chunks = q.all()
    return [
        {
            "id": ch.id,
            "document_title": ch.document.title if ch.document else "",
            "doi": ch.document.doi if ch.document else None,
            "source_url": ch.document.source_url if ch.document else "",
            "publisher": ch.document.source.publisher if (ch.document and ch.document.source) else "NASA PSI",
            "external_investigation_id": ch.document.investigation.external_id
            if (ch.document and ch.document.investigation)
            else None,
            "section_title": ch.section_title,
            "content_text": ch.content_text,
            "combustion_domain": ch.combustion_domain,
            "gravity_regime": ch.gravity_regime,
            "fuel_tags": ch.fuel_tags,
            "keywords": ch.keywords,
        }
        for ch in chunks
    ]


@app.post("/api/assistant/query")
def query_research_assistant(req: AssistantQueryRequest, db: Session = Depends(get_db)):
    return run_hybrid_assistant_query(db, req)


@app.post("/api/llm/ask")
def query_flare_llm_engine(req: AssistantQueryRequest, db: Session = Depends(get_db)):
    return run_hybrid_assistant_query(db, req)["flare_llm_response"]
