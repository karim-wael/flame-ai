import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from .config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def gen_uuid() -> str:
    return str(uuid.uuid4())


class DataSource(Base):
    __tablename__ = "data_sources"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    publisher = Column(String(128), nullable=False)
    source_name = Column(String(256), nullable=False)
    source_url = Column(Text, nullable=False)
    license = Column(String(256), nullable=False)
    access_date = Column(String(64), nullable=False)
    citation_text = Column(Text, nullable=False)
    priority = Column(String(16), nullable=False, default="P0")
    domain_track = Column(String(64), nullable=False, default="microgravity_research")

    investigations = relationship("Investigation", back_populates="source", cascade="all, delete-orphan")
    field_mappings = relationship("FieldMapping", back_populates="source", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="source", cascade="all, delete-orphan")


class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=False)
    external_id = Column(String(64), nullable=False, unique=True, index=True)
    title = Column(String(512), nullable=False)
    doi = Column(String(128), nullable=True)
    version = Column(String(64), nullable=False)
    project_type = Column(String(128), nullable=False)
    platform = Column(String(128), nullable=False)
    gravity_regime = Column(String(64), nullable=False, index=True)
    combustion_domain = Column(String(64), nullable=False, index=True)
    priority = Column(String(16), nullable=False, default="P0")
    start_date = Column(String(64), nullable=True)
    end_date = Column(String(64), nullable=True)
    source_url = Column(Text, nullable=False)
    source_metadata = Column(JSON, nullable=False, default=dict)

    source = relationship("DataSource", back_populates="investigations")
    experiment_runs = relationship("ExperimentRun", back_populates="investigation", cascade="all, delete-orphan")
    source_files = relationship("SourceFile", back_populates="investigation", cascade="all, delete-orphan")
    knowledge_documents = relationship("KnowledgeDocument", back_populates="investigation")


class SourceFile(Base):
    __tablename__ = "source_files"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    file_name = Column(String(256), nullable=False)
    file_url = Column(Text, nullable=False)
    mime_type = Column(String(128), nullable=False)
    file_size = Column(Integer, nullable=False)
    checksum_sha256 = Column(String(64), nullable=False)
    file_role = Column(String(128), nullable=False)
    version = Column(String(64), nullable=False)
    local_storage_key = Column(Text, nullable=False)

    investigation = relationship("Investigation", back_populates="source_files")
    measurements = relationship("Measurement", back_populates="source_file")


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=False)
    run_code = Column(String(128), nullable=False, unique=True, index=True)
    combustion_domain = Column(String(64), nullable=False, index=True)
    gravity_regime = Column(String(64), nullable=False, index=True)
    platform = Column(String(128), nullable=False)
    fuel_material = Column(String(256), nullable=False)
    fuel_state = Column(String(64), nullable=False)
    oxidizer = Column(String(128), nullable=False)
    oxygen_fraction = Column(Float, nullable=True)
    oxygen_missing_reason = Column(String(64), nullable=True)
    pressure_value = Column(Float, nullable=True)
    pressure_unit = Column(String(32), nullable=True)
    pressure_normalized_kpa = Column(Float, nullable=True)
    pressure_missing_reason = Column(String(64), nullable=True)
    flow_velocity_value = Column(Float, nullable=True)
    flow_velocity_unit = Column(String(32), nullable=True)
    flow_velocity_normalized_cm_s = Column(Float, nullable=True)
    flow_velocity_missing_reason = Column(String(64), nullable=True)
    temperature_value = Column(Float, nullable=True)
    temperature_unit = Column(String(32), nullable=True)
    burner_or_sample_geometry = Column(String(256), nullable=True)
    droplet_diameter_mm = Column(Float, nullable=True)
    sample_orientation = Column(String(128), nullable=True)
    test_environment = Column(String(256), nullable=False)
    is_terrestrial_baseline = Column(Boolean, nullable=False, default=False)
    run_metadata = Column(JSON, nullable=False, default=dict)

    investigation = relationship("Investigation", back_populates="experiment_runs")
    measurements = relationship("Measurement", back_populates="run", cascade="all, delete-orphan")
    derived_results = relationship("DerivedResult", back_populates="run", cascade="all, delete-orphan")


class Measurement(Base):
    __tablename__ = "measurements"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("experiment_runs.id"), nullable=False)
    variable_name = Column(String(128), nullable=False)
    canonical_field = Column(String(128), nullable=False, index=True)
    value_numeric = Column(Float, nullable=True)
    value_text = Column(Text, nullable=True)
    unit = Column(String(64), nullable=True)
    normalized_value = Column(Float, nullable=True)
    normalized_unit = Column(String(64), nullable=True)
    value_status = Column(String(32), nullable=False)
    measurement_time = Column(String(64), nullable=True)
    uncertainty = Column(Float, nullable=True)
    measurement_method = Column(String(256), nullable=True)
    missing_reason = Column(String(64), nullable=True)
    source_file_id = Column(String(36), ForeignKey("source_files.id"), nullable=True)
    notes = Column(Text, nullable=True)

    run = relationship("ExperimentRun", back_populates="measurements")
    source_file = relationship("SourceFile", back_populates="measurements")


class FieldMapping(Base):
    __tablename__ = "field_mappings"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=False)
    source_field = Column(String(128), nullable=False)
    canonical_field = Column(String(128), nullable=False)
    source_unit = Column(String(64), nullable=True)
    canonical_unit = Column(String(64), nullable=True)
    transform_description = Column(Text, nullable=False)
    mapping_version = Column(String(32), nullable=False)

    source = relationship("DataSource", back_populates="field_mappings")


class DerivedResult(Base):
    __tablename__ = "derived_results"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    run_id = Column(String(36), ForeignKey("experiment_runs.id"), nullable=False)
    method_name = Column(String(128), nullable=False)
    method_version = Column(String(32), nullable=False)
    result_name = Column(String(128), nullable=False)
    result_value = Column(Float, nullable=True)
    result_unit = Column(String(64), nullable=True)
    explanation = Column(Text, nullable=False)
    input_measurement_ids = Column(JSON, nullable=False, default=list)

    run = relationship("ExperimentRun", back_populates="derived_results")


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=True)
    source_id = Column(String(36), ForeignKey("data_sources.id"), nullable=False)
    title = Column(String(512), nullable=False)
    doc_type = Column(String(64), nullable=False)
    doi = Column(String(128), nullable=True)
    source_url = Column(Text, nullable=False)
    publication_year = Column(Integer, nullable=True)
    authors = Column(Text, nullable=True)
    checksum_sha256 = Column(String(64), nullable=False)

    source = relationship("DataSource", back_populates="knowledge_documents")
    investigation = relationship("Investigation", back_populates="knowledge_documents")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(String(36), primary_key=True, default=gen_uuid)
    document_id = Column(String(36), ForeignKey("knowledge_documents.id"), nullable=False)
    investigation_id = Column(String(36), ForeignKey("investigations.id"), nullable=True)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(256), nullable=False)
    content_text = Column(Text, nullable=False)
    combustion_domain = Column(String(64), nullable=False, index=True)
    gravity_regime = Column(String(64), nullable=False, index=True)
    fuel_tags = Column(JSON, nullable=False, default=list)
    keywords = Column(JSON, nullable=False, default=list)
    embedding_json = Column(JSON, nullable=False, default=list)

    document = relationship("KnowledgeDocument", back_populates="chunks")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
