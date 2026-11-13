from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

GravityRegime = Literal["microgravity", "normal_gravity", "partial_gravity", "unknown"]
CombustionDomain = Literal["solid", "gas", "liquid_droplet", "aerosol_smoke", "mixed", "unknown"]
ValueStatus = Literal["measured", "derived", "missing", "not_applicable"]
MissingReason = Literal[
    "not_reported",
    "not_measured",
    "not_applicable",
    "unavailable_in_source",
    "parsing_failed",
]


class CompareRequest(BaseModel):
    target_domain: CombustionDomain = Field(
        default="solid",
        description="Target combustion domain. Comparisons are strictly domain-gated by default.",
    )
    target_gravity: GravityRegime = Field(
        default="microgravity",
        description="Target gravity regime (microgravity, normal_gravity, partial_gravity, unknown).",
    )
    oxygen_fraction: float = Field(
        default=0.21,
        ge=0.05,
        le=1.0,
        description="Target oxygen mole/volume fraction (e.g., 0.21 for 21% O2).",
    )
    pressure_kpa: float = Field(
        default=101.3,
        ge=10.0,
        le=300.0,
        description="Target ambient pressure normalized in kPa (e.g., 101.3 kPa = 14.7 psia = 1 atm).",
    )
    flow_velocity_cm_s: float = Field(
        default=8.0,
        ge=0.0,
        le=200.0,
        description="Target forced oxidizer flow velocity normalized in cm/s.",
    )
    weights: Dict[str, float] = Field(
        default_factory=lambda: {"oxygen_fraction": 0.45, "pressure_kpa": 0.25, "flow_velocity_cm_s": 0.30},
        description="Feature weights w1 (O2), w2 (Pressure), w3 (Flow velocity).",
    )
    include_terrestrial_baseline: bool = Field(
        default=True,
        description="Return Earth-based FSRI reference records in a separate baseline track (never merged into microgravity ranking).",
    )
    candidate_run_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional explicit subset of experiment_run IDs or run_codes to evaluate.",
    )


class IngestionJobRequest(BaseModel):
    source_filter: Optional[str] = Field(
        default=None,
        description="Optional publisher or external investigation ID to ingest (e.g. 'NASA PSI', 'JAXA DARTS', 'UL FSRI', or 'ALL').",
    )
    force_refresh: bool = Field(
        default=True,
        description="Re-run the 7-step Discover -> Acquire -> Parse -> Normalize -> Validate -> Publish -> Audit workflow.",
    )


class AssistantQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        description="Scientific question for Hybrid Retrieval (Semantic + Keyword + SQL).",
    )
    combustion_domain: Optional[CombustionDomain] = Field(
        default=None,
        description="Optional combustion domain filter.",
    )
    gravity_regime: Optional[GravityRegime] = Field(
        default=None,
        description="Optional gravity regime filter.",
    )
    fuel_filter: Optional[str] = Field(
        default=None,
        description="Optional fuel/material keyword filter.",
    )
    top_k_chunks: int = Field(default=4, ge=1, le=8)
    top_k_experiments: int = Field(default=5, ge=1, le=12)
