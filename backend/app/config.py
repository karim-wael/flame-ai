import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ROOT_DIR = BASE_DIR.parent

load_dotenv(ROOT_DIR / ".env")
load_dotenv(BASE_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'flare_ai.db').as_posix()}")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("AI_API_KEY") or ""
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY") or ""
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
INGESTION_API_TOKEN = os.getenv("INGESTION_API_TOKEN", "flare-dev-ingestion-token-2026")

# Real Team Data Handoff & Ranking Engine Directories
HANDOFF_DIR = Path(os.getenv("FLARE_DATA_DIR", str(ROOT_DIR / "FLARE_AI_Data_Handoff")))
RANKING_DIR = ROOT_DIR / "flare_ranking"

# Section 6: Controlled Vocabularies
GRAVITY_REGIMES = ("microgravity", "normal_gravity", "partial_gravity", "unknown")
COMBUSTION_DOMAINS = ("solid", "gas", "liquid_droplet", "aerosol_smoke", "mixed", "unknown")
VALUE_STATUSES = ("measured", "derived", "missing", "not_applicable")
MISSING_REASONS = (
    "not_reported",
    "not_measured",
    "not_applicable",
    "unavailable_in_source",
    "parsing_failed",
    "invalid_value",
)

# Section 7: Scientific Comparison & Product Guardrails
SCIENTIFIC_DISCLAIMER = (
    "FLARE AI is a research and decision-support prototype, NOT a certified spacecraft fire-safety system. "
    "A similarity score represents closeness of experimental conditions (research relevance) within a compatible "
    "combustion domain—it is NOT an ignition probability, fire-risk score, or prediction of lunar/Martian fire behavior."
)
