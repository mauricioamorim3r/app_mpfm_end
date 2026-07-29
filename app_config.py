from __future__ import annotations

import json
import os
from pathlib import Path

# Load .env file if present (local/dev only — production uses real env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=Path(__file__).parent / ".env", override=False)
except ImportError:
    pass


BASE_DIR = Path(__file__).parent
WORK_DIR = Path(os.getenv("MPFM_DATA_DIR", str(BASE_DIR / "data")))
UPLOAD_DIR = WORK_DIR / "uploads"
OUTPUT_DIR = WORK_DIR / "outputs"
STATIC_DIR = BASE_DIR / "static"
DB_PATH = Path(os.getenv("MPFM_DB_PATH", str(WORK_DIR / "mpfm_local.db")))

APP_TITLE = "MPFM Manager"
APP_VERSION = "4.1"
DEFAULT_HOST = os.getenv("MPFM_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("MPFM_PORT", "8765"))
PUBLIC_BASE_URL = os.getenv("MPFM_PUBLIC_BASE_URL", f"http://localhost:{DEFAULT_PORT}")

MONTH_PT = {
    "01": "JAN",
    "02": "FEV",
    "03": "MAR",
    "04": "ABR",
    "05": "MAI",
    "06": "JUN",
    "07": "JUL",
    "08": "AGO",
    "09": "SET",
    "10": "OUT",
    "11": "NOV",
    "12": "DEZ",
}

DEFAULT_DENSITY = 790.78
BBL_PER_M3 = 6.28981
GAS_SM3_PER_BOE = 170.0

# --- Microsoft Foundry / Azure AI ---
AZURE_AI_PROJECT_ENDPOINT: str = os.getenv("AZURE_AI_PROJECT_ENDPOINT", "")
AZURE_AI_API_KEY: str = os.getenv("AZURE_AI_API_KEY", "")
AZURE_AI_MODEL: str = os.getenv("AZURE_AI_MODEL", "gpt-4o")

# --- OpenAI ---
OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")

# --- Anthropic / Claude ---
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL: str = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

# --- Google Gemini ---
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
AI_MASTER_PROMPT: str = os.getenv("AI_MASTER_PROMPT", "")

# --- Moonshot / Kimi ---
MOONSHOT_API_KEY: str = os.getenv("MOONSHOT_API_KEY", "")
MOONSHOT_BASE_URL: str = os.getenv("MOONSHOT_BASE_URL", "https://api.moonshot.ai/v1")
MOONSHOT_MODEL: str = os.getenv("MOONSHOT_MODEL", "moonshot-v1-8k")

# Provider padrão: Gemini é o único provider habilitado na interface corporativa.
AI_DEFAULT_PROVIDER: str = os.getenv("AI_DEFAULT_PROVIDER", "gemini")

# --- Identidade da empresa (uso interno) ---
COMPANY_NAME: str = os.getenv("MPFM_COMPANY_NAME", "Equinor Brasil Energia Ltda.")
COMPANY_INTERNAL_NOTE: str = "Sistema de medição multifásica — uso interno"

# --- Autenticação HTTP Basic ---
AUTH_ENABLED: bool = os.getenv("MPFM_AUTH_ENABLED", "true").lower() not in {"0", "false", "no", "off"}
AUTH_USERNAME: str = os.getenv("MPFM_AUTH_USER", "")
AUTH_PASSWORD: str = os.getenv("MPFM_AUTH_PASS", "")



def ensure_workdirs() -> None:
    for directory in (WORK_DIR, UPLOAD_DIR, OUTPUT_DIR, STATIC_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def get_inactive_tag_associados() -> list[str]:
    """Returns normalized sistema names (matching the 'tag' column in measurements_curated)
    for all entries where ativo=False in cadastro.json.
    Normalization: spaces replaced with underscores, matching the Excel Tag column format.
    """
    cad_path = WORK_DIR / "cadastro.json"
    try:
        with open(cad_path, encoding="utf-8") as f:
            cad = json.load(f)
    except Exception:
        return []
    inactive: list[str] = []
    for section in ("banks_subsea", "banks_topside"):
        for entry in cad.get(section, []):
            if not entry.get("ativo", True):
                sistema = entry.get("sistema", "").strip()
                if sistema:
                    inactive.append(sistema.replace(" ", "_"))
    return inactive
