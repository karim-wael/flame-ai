-- FLARE AI — PostgreSQL + pgvector Canonical Relational & Hybrid Knowledge Schema
-- NASA Space Apps Challenge 2026 | Flame in Freefall

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 1. data_sources
CREATE TABLE IF NOT EXISTS data_sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    publisher VARCHAR(128) NOT NULL,
    source_name VARCHAR(256) NOT NULL,
    source_url TEXT NOT NULL,
    license VARCHAR(256) NOT NULL,
    access_date VARCHAR(64) NOT NULL,
    citation_text TEXT NOT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'P0',
    domain_track VARCHAR(64) NOT NULL DEFAULT 'microgravity_research'
);

-- 2. investigations
CREATE TABLE IF NOT EXISTS investigations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    external_id VARCHAR(64) NOT NULL UNIQUE,
    title VARCHAR(512) NOT NULL,
    doi VARCHAR(128),
    version VARCHAR(64) NOT NULL,
    project_type VARCHAR(128) NOT NULL,
    platform VARCHAR(128) NOT NULL,
    gravity_regime VARCHAR(64) NOT NULL CHECK (gravity_regime IN ('microgravity', 'normal_gravity', 'partial_gravity', 'unknown')),
    combustion_domain VARCHAR(64) NOT NULL CHECK (combustion_domain IN ('solid', 'gas', 'liquid_droplet', 'aerosol_smoke', 'mixed', 'unknown')),
    priority VARCHAR(16) NOT NULL DEFAULT 'P0',
    start_date VARCHAR(64),
    end_date VARCHAR(64),
    source_url TEXT NOT NULL,
    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 3. source_files
CREATE TABLE IF NOT EXISTS source_files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    file_name VARCHAR(256) NOT NULL,
    file_url TEXT NOT NULL,
    mime_type VARCHAR(128) NOT NULL,
    file_size INTEGER NOT NULL,
    checksum_sha256 VARCHAR(64) NOT NULL,
    file_role VARCHAR(128) NOT NULL,
    version VARCHAR(64) NOT NULL,
    local_storage_key TEXT NOT NULL
);

-- 4. experiment_runs
CREATE TABLE IF NOT EXISTS experiment_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID NOT NULL REFERENCES investigations(id) ON DELETE CASCADE,
    run_code VARCHAR(128) NOT NULL UNIQUE,
    combustion_domain VARCHAR(64) NOT NULL CHECK (combustion_domain IN ('solid', 'gas', 'liquid_droplet', 'aerosol_smoke', 'mixed', 'unknown')),
    gravity_regime VARCHAR(64) NOT NULL CHECK (gravity_regime IN ('microgravity', 'normal_gravity', 'partial_gravity', 'unknown')),
    platform VARCHAR(128) NOT NULL,
    fuel_material VARCHAR(256) NOT NULL,
    fuel_state VARCHAR(64) NOT NULL,
    oxidizer VARCHAR(128) NOT NULL,
    oxygen_fraction DOUBLE PRECISION,
    oxygen_missing_reason VARCHAR(64),
    pressure_value DOUBLE PRECISION,
    pressure_unit VARCHAR(32),
    pressure_normalized_kpa DOUBLE PRECISION,
    pressure_missing_reason VARCHAR(64),
    flow_velocity_value DOUBLE PRECISION,
    flow_velocity_unit VARCHAR(32),
    flow_velocity_normalized_cm_s DOUBLE PRECISION,
    flow_velocity_missing_reason VARCHAR(64),
    temperature_value DOUBLE PRECISION,
    temperature_unit VARCHAR(32),
    burner_or_sample_geometry VARCHAR(256),
    droplet_diameter_mm DOUBLE PRECISION,
    sample_orientation VARCHAR(128),
    test_environment VARCHAR(256) NOT NULL,
    is_terrestrial_baseline BOOLEAN NOT NULL DEFAULT FALSE,
    run_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 5. measurements
CREATE TABLE IF NOT EXISTS measurements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    variable_name VARCHAR(128) NOT NULL,
    canonical_field VARCHAR(128) NOT NULL,
    value_numeric DOUBLE PRECISION,
    value_text TEXT,
    unit VARCHAR(64),
    normalized_value DOUBLE PRECISION,
    normalized_unit VARCHAR(64),
    value_status VARCHAR(32) NOT NULL CHECK (value_status IN ('measured', 'derived', 'missing', 'not_applicable')),
    measurement_time VARCHAR(64),
    uncertainty DOUBLE PRECISION,
    measurement_method VARCHAR(256),
    missing_reason VARCHAR(64) CHECK (missing_reason IS NULL OR missing_reason IN ('not_reported', 'not_measured', 'not_applicable', 'unavailable_in_source', 'parsing_failed')),
    source_file_id UUID REFERENCES source_files(id) ON DELETE SET NULL,
    notes TEXT
);

-- 6. field_mappings
CREATE TABLE IF NOT EXISTS field_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    source_field VARCHAR(128) NOT NULL,
    canonical_field VARCHAR(128) NOT NULL,
    source_unit VARCHAR(64),
    canonical_unit VARCHAR(64),
    transform_description TEXT NOT NULL,
    mapping_version VARCHAR(32) NOT NULL
);

-- 7. derived_results
CREATE TABLE IF NOT EXISTS derived_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    run_id UUID NOT NULL REFERENCES experiment_runs(id) ON DELETE CASCADE,
    method_name VARCHAR(128) NOT NULL,
    method_version VARCHAR(32) NOT NULL,
    result_name VARCHAR(128) NOT NULL,
    result_value DOUBLE PRECISION,
    result_unit VARCHAR(64),
    explanation TEXT NOT NULL,
    input_measurement_ids JSONB NOT NULL DEFAULT '[]'::jsonb
);

-- 8. knowledge_documents (Hybrid Knowledge Base — PDF/DOC/Reports)
CREATE TABLE IF NOT EXISTS knowledge_documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    investigation_id UUID REFERENCES investigations(id) ON DELETE SET NULL,
    source_id UUID NOT NULL REFERENCES data_sources(id) ON DELETE CASCADE,
    title VARCHAR(512) NOT NULL,
    doc_type VARCHAR(64) NOT NULL,
    doi VARCHAR(128),
    source_url TEXT NOT NULL,
    publication_year INTEGER,
    authors TEXT,
    checksum_sha256 VARCHAR(64) NOT NULL
);

-- 9. knowledge_chunks (Embeddings + Chunks + Source References)
CREATE TABLE IF NOT EXISTS knowledge_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    investigation_id UUID REFERENCES investigations(id) ON DELETE SET NULL,
    chunk_index INTEGER NOT NULL,
    section_title VARCHAR(256) NOT NULL,
    content_text TEXT NOT NULL,
    combustion_domain VARCHAR(64) NOT NULL,
    gravity_regime VARCHAR(64) NOT NULL,
    fuel_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
    keywords JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    embedding vector(64)
);

CREATE INDEX IF NOT EXISTS idx_investigations_domain_gravity ON investigations(combustion_domain, gravity_regime);
CREATE INDEX IF NOT EXISTS idx_runs_domain_gravity ON experiment_runs(combustion_domain, gravity_regime, is_terrestrial_baseline);
CREATE INDEX IF NOT EXISTS idx_measurements_run_canonical ON measurements(run_id, canonical_field);
CREATE INDEX IF NOT EXISTS idx_chunks_domain_gravity ON knowledge_chunks(combustion_domain, gravity_regime);
