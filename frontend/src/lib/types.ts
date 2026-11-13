export type GravityRegime = "microgravity" | "normal_gravity" | "partial_gravity" | "unknown";
export type CombustionDomain = "solid" | "gas" | "liquid_droplet" | "aerosol_smoke" | "mixed" | "unknown";
export type ValueStatus = "measured" | "derived" | "missing" | "not_applicable";

export interface Measurement {
  id: string;
  variable_name: string;
  canonical_field: string;
  value_numeric: number | null;
  value_text?: string | null;
  unit: string | null;
  normalized_value: number | null;
  normalized_unit: string | null;
  value_status: ValueStatus;
  uncertainty?: number | null;
  measurement_method?: string | null;
  missing_reason?: string | null;
  source_file_id?: string | null;
  notes?: string | null;
}

export interface DerivedResult {
  id: string;
  method_name: string;
  method_version: string;
  result_name: string;
  result_value: number | null;
  result_unit: string | null;
  explanation: string;
  input_measurement_ids: string[];
}

export interface SourceFile {
  id: string;
  file_name: string;
  file_url: string;
  mime_type: string;
  file_size: number;
  checksum_sha256: string;
  file_role: string;
  version: string;
  local_storage_key: string;
}

export interface ExperimentRun {
  id: string;
  run_code: string;
  investigation_id: string;
  external_investigation_id: string;
  investigation_title: string;
  publisher: string;
  doi: string | null;
  source_url: string;
  combustion_domain: CombustionDomain;
  gravity_regime: GravityRegime;
  platform: string;
  fuel_material: string;
  fuel_state: string;
  oxidizer: string;
  oxygen_fraction: number | null;
  oxygen_missing_reason: string | null;
  pressure_value: number | null;
  pressure_unit: string | null;
  pressure_normalized_kpa: number | null;
  pressure_missing_reason: string | null;
  flow_velocity_value: number | null;
  flow_velocity_unit: string | null;
  flow_velocity_normalized_cm_s: number | null;
  flow_velocity_missing_reason: string | null;
  temperature_value: number | null;
  temperature_unit: string | null;
  burner_or_sample_geometry: string | null;
  droplet_diameter_mm: number | null;
  sample_orientation: string | null;
  test_environment: string;
  is_terrestrial_baseline: boolean;
  run_metadata: Record<string, unknown>;
  measurements: Measurement[];
  derived_results: DerivedResult[];
}

export interface InvestigationSummary {
  id: string;
  external_id: string;
  title: string;
  publisher: string;
  domain_track: string;
  doi: string | null;
  version: string;
  project_type: string;
  platform: string;
  gravity_regime: GravityRegime;
  combustion_domain: CombustionDomain;
  priority: string;
  start_date: string | null;
  end_date: string | null;
  source_url: string;
  source_metadata: Record<string, unknown>;
  run_count: number;
  file_count: number;
}

export interface InvestigationDetail extends InvestigationSummary {
  license: string;
  citation_text: string;
  source_files: SourceFile[];
  experiment_runs: ExperimentRun[];
}

export interface DataSourceItem {
  id: string;
  publisher: string;
  source_name: string;
  source_url: string;
  license: string;
  access_date: string;
  citation_text: string;
  priority: string;
  domain_track: string;
  investigation_count: number;
  field_mappings: {
    id: string;
    source_field: string;
    canonical_field: string;
    source_unit: string | null;
    canonical_unit: string | null;
    transform_description: string;
    mapping_version: string;
  }[];
}

export interface CompareRankedItem {
  rank?: number;
  run_id: string;
  run_code: string;
  investigation_id: string;
  investigation_external_id: string;
  investigation_title: string;
  publisher: string;
  doi: string | null;
  source_url: string;
  source_file_name: string | null;
  source_file_checksum: string | null;
  combustion_domain: CombustionDomain;
  gravity_regime: GravityRegime;
  is_terrestrial_baseline: boolean;
  platform: string;
  fuel_material: string;
  oxygen_fraction: number | null;
  pressure_normalized_kpa: number | null;
  pressure_original: string | null;
  flow_velocity_normalized_cm_s: number | null;
  flow_velocity_original: string | null;
  distance_d: number;
  condition_closeness_index: number;
  feature_coverage_ratio: number;
  missing_features: { feature: string; missing_reason: string }[];
  feature_breakdown: Record<string, Record<string, unknown>>;
  outcomes: Measurement[];
  explanation: string;
  baseline_separation_note?: string;
}

export interface CompareResponse {
  scientific_disclaimer: string;
  formula: string;
  scaler_audit: {
    scaler_type: string;
    feature_spans: Record<string, { min: number; max: number; unit: string }>;
    normalized_weights: Record<string, number>;
    target_conditions: {
      target_domain: CombustionDomain;
      target_gravity: GravityRegime;
      oxygen_fraction: number;
      pressure_kpa: number;
      flow_velocity_cm_s: number;
    };
  };
  compatible_microgravity_ranking: CompareRankedItem[];
  terrestrial_baseline_track: CompareRankedItem[];
  excluded_incompatible_domains: {
    run_id: string;
    run_code: string;
    investigation_external_id: string;
    investigation_title: string;
    record_domain: CombustionDomain;
    target_domain: CombustionDomain;
    gravity_regime: GravityRegime;
    fuel_material: string;
    rejection_reason: string;
  }[];
}

export interface AssistantResponse {
  question: string;
  scientific_disclaimer: string;
  retrieval_pipeline_trace: { step: string; detail: string }[];
  published_scientific_evidence: {
    chunk_id: string;
    document_title: string;
    doc_type: string;
    authors: string | null;
    publication_year: number | null;
    publisher: string;
    external_investigation_id: string;
    doi: string | null;
    source_url: string;
    section_title: string;
    content_text: string;
    combustion_domain: CombustionDomain;
    gravity_regime: GravityRegime;
    fuel_tags: string[];
    keywords: string[];
    semantic_score: number;
    keyword_score: number;
    hybrid_score: number;
  }[];
  structured_sql_experiments: {
    run_id: string;
    run_code: string;
    external_investigation_id: string;
    investigation_title: string;
    doi: string | null;
    source_url: string;
    combustion_domain: CombustionDomain;
    gravity_regime: GravityRegime;
    is_terrestrial_baseline: boolean;
    platform: string;
    fuel_material: string;
    oxygen_fraction: number | null;
    pressure_normalized_kpa: number | null;
    flow_velocity_normalized_cm_s: number | null;
    flow_velocity_missing_reason: string | null;
    sql_relevance_score: number;
    measurements: Measurement[];
  }[];
  generated_interpretation: {
    label: string;
    synthesis_mode: string;
    markdown_content: string;
    citations: {
      external_id: string;
      title: string;
      doi: string | null;
      source_url: string;
      publisher: string;
    }[];
  };
}

