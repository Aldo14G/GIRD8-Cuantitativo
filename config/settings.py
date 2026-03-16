"""
Configuration settings for NL Data Quality Pipeline.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

CKAN_BASE_URL = os.getenv("CKAN_BASE_URL", "https://catalogodatos.nl.gob.mx")
CKAN_API_BASE = f"{CKAN_BASE_URL}/api/3/action"

RATE_LIMIT_SECONDS = float(os.getenv("RATE_LIMIT_SECONDS", "0.4"))
MAX_DATASETS = int(os.getenv("MAX_DATASETS", "68"))

DATA_ROOT = PROJECT_ROOT / os.getenv("DATA_ROOT", "data")
DATA_RAW = DATA_ROOT / "raw"
DATA_PROCESSED = DATA_ROOT / "processed"
DATA_OUTPUT = DATA_ROOT / "output"

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

HEADERS = {
    "User-Agent": "InvestigacionCalidadDatosNL/2.0 (investigacion academica 2026)"
}
