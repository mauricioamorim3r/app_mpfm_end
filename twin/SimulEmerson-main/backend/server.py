"""
Twin MPFM Bacalhau — FastAPI backend.

Responsabilidade:
- Schemas Pydantic (entrada/saída HTTP).
- Persistência MongoDB (analyses, pvt_catalog, mpfm_records).
- Rotas /api/* (orquestração).

Os motores de cálculo metrológico vivem em `services.calculations`;
o leitor de planilhas em `services.importers`.
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
import logging
import os
import uuid

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, Field
from starlette.middleware.cors import CORSMiddleware

from services.calculations import (
    CONSTANTS,
    DEFAULT_PVT,
    DEFAULT_SEPARATOR,
    analyze,
    build_memorial,
    separator_balance,
)
from services.importers import import_mpfm_xlsx

# ==================== Bootstrap ====================
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("twin_mpfm")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Twin MPFM backend starting (FastAPI lifespan)")
    yield
    logger.info("Twin MPFM backend shutting down")
    client.close()


app = FastAPI(title="Twin MPFM Bacalhau API", version="4.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api")


# ==================== Schemas (entrada HTTP) ====================
class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    well: str = "PE-4"
    windowLabel: str = "01/05/2026 00:00 - 02/05/2026 00:00"
    pressure: float = Field(default=203.5, ge=0, description="Pressão (barg)")
    temperature: float = Field(default=67.8, ge=-273.15, description="Temperatura (°C)")
    qo: float = Field(default=800.34, ge=0, description="Vazão óleo (m³/d)")
    qw: float = Field(default=0.04, ge=0, description="Vazão água (m³/d)")
    qg: float = Field(default=252796.0, ge=0, description="Vazão gás (Sm³/d)")
    gasLift: float = Field(default=0.0, ge=0, description="Gas lift (Sm³/d)")
    comparisonPair: str = "Subsea × Topside"


class SeparatorInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    GSV_sep: float = Field(default=DEFAULT_SEPARATOR["GSV_sep"], ge=0)
    BSW: float = Field(default=DEFAULT_SEPARATOR["BSW"], ge=0, le=100)
    SF_sep_tank: float = Field(default=DEFAULT_SEPARATOR["SF_sep_tank"], gt=0, le=1.5)
    rho_oil_STO: float = Field(default=DEFAULT_SEPARATOR["rho_oil_STO"], gt=0)
    V_gas_sep_std: float = Field(default=DEFAULT_SEPARATOR["V_gas_sep_std"], ge=0)
    deltaRs_sep_tank: float = Field(default=DEFAULT_SEPARATOR["deltaRs_sep_tank"], ge=0)
    rho_gas_std: float = Field(default=0.899, gt=0)
    V_water_free_std: float = Field(default=DEFAULT_SEPARATOR["V_water_free_std"], ge=0)
    rho_water_20: float = Field(default=DEFAULT_SEPARATOR["rho_water_20"], gt=0)
    U_MPFM: float = Field(default=DEFAULT_SEPARATOR["U_MPFM"], ge=0)
    U_REF: float = Field(default=DEFAULT_SEPARATOR["U_REF"], ge=0)


class PVTInput(BaseModel):
    model_config = ConfigDict(extra="ignore")
    source: str = DEFAULT_PVT["source"]
    eos: str = DEFAULT_PVT["eos"]
    fluidId: str = DEFAULT_PVT["fluidId"]
    SF_sep_tank: float = DEFAULT_PVT["SF_sep_tank"]
    deltaRs_sep_tank: float = DEFAULT_PVT["deltaRs_sep_tank"]
    rho_oil_STO: float = DEFAULT_PVT["rho_oil_STO"]
    rho_gas_std: float = DEFAULT_PVT["rho_gas_std"]
    status: str = DEFAULT_PVT["status"]
    nativeFile: bool = DEFAULT_PVT["nativeFile"]


class AnalysisRequest(BaseModel):
    input: AnalysisInput = Field(default_factory=AnalysisInput)
    separator: SeparatorInput = Field(default_factory=SeparatorInput)
    pvt: PVTInput = Field(default_factory=PVTInput)
    persist: bool = True


class PVTCreateRequest(BaseModel):
    fluidId: str
    source: Optional[str] = None
    eos: Optional[str] = None
    SF_sep_tank: Optional[float] = None
    deltaRs_sep_tank: Optional[float] = None
    rho_oil_STO: Optional[float] = None
    rho_gas_std: Optional[float] = None
    status: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)


# ==================== Helpers ====================
def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


# ==================== Routes ====================
@api_router.get("/health")
async def health():
    return {"status": "ok", "app": "Twin MPFM", "version": "4.0.0"}


@api_router.get("/constants")
async def constants():
    return CONSTANTS


@api_router.post("/consultor/analyze")
async def analyze_endpoint(req: AnalysisRequest):
    result = analyze(req.input.model_dump(),
                     req.separator.model_dump(),
                     req.pvt.model_dump())
    if req.persist:
        analysis_id = new_id()
        doc = {
            "id": analysis_id,
            "created_at": now_iso(),
            "well": result["input"].get("well"),
            "window_label": result["input"].get("windowLabel"),
            "comparison_pair": result["input"].get("comparisonPair"),
            "status": result["metrics"].get("technicalStatus"),
            "gvf": result["metrics"].get("gvf"),
            "wlr": result["metrics"].get("wlr"),
            "gor": result["metrics"].get("gor"),
            "iaj": result["metrics"].get("iaj"),
            "factor_suggested": result["metrics"].get("factorSuggested"),
            "payload": result,
        }
        await db.analyses.insert_one(doc)
        result["analysis_id"] = analysis_id
    return result


@api_router.post("/separator-balance/calculate")
async def separator_balance_endpoint(req: SeparatorInput):
    return separator_balance(req.model_dump())


@api_router.get("/analyses")
async def analyses(limit: int = 50):
    docs = await db.analyses.find(
        {},
        {"_id": 0, "id": 1, "created_at": 1, "well": 1, "window_label": 1,
         "comparison_pair": 1, "status": 1, "gvf": 1, "wlr": 1, "gor": 1,
         "iaj": 1, "factor_suggested": 1},
    ).sort("created_at", -1).to_list(limit)
    return docs


@api_router.get("/analyses/{analysis_id}")
async def analysis_detail(analysis_id: str):
    item = await db.analyses.find_one({"id": analysis_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Analysis not found")
    return item.get("payload") or item


@api_router.get("/analyses/{analysis_id}/memorial", response_class=PlainTextResponse)
async def analysis_memorial(analysis_id: str):
    item = await db.analyses.find_one({"id": analysis_id}, {"_id": 0})
    if not item:
        raise HTTPException(404, "Analysis not found")
    payload = item.get("payload") or item
    return build_memorial(payload)


@api_router.get("/pvt/catalog")
async def pvt_catalog():
    docs = await db.pvt_catalog.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return docs


@api_router.post("/pvt/catalog")
async def create_pvt(req: PVTCreateRequest):
    payload = {**(req.payload or {}), **req.model_dump(exclude={"payload"})}
    item_id = new_id()
    doc = {
        "id": item_id,
        "created_at": now_iso(),
        "fluid_id": payload.get("fluidId") or payload.get("fluid_id"),
        "source": payload.get("source"),
        "eos": payload.get("eos"),
        "sf_sep_tank": payload.get("SF_sep_tank") or payload.get("sf_sep_tank"),
        "delta_rs_sep_tank": payload.get("deltaRs_sep_tank") or payload.get("delta_rs_sep_tank"),
        "rho_oil_sto": payload.get("rho_oil_STO") or payload.get("rho_oil_sto"),
        "rho_gas_std": payload.get("rho_gas_std"),
        "status": payload.get("status"),
        "payload": payload,
    }
    await db.pvt_catalog.insert_one(doc)
    return {"id": item_id, "status": "created"}


@api_router.post("/import/mpfm-xlsx")
async def import_mpfm(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xlsm")):
        raise HTTPException(400, "Upload an .xlsx or .xlsm file")
    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    records: list = []  # defensive default — overwritten on success, never read after raise
    try:
        records = import_mpfm_xlsx(content)
    except Exception as exc:  # planilha mal-formada não deve gerar 500
        logger.warning("import_mpfm_xlsx failed for %s: %s", file.filename, exc)
        raise HTTPException(400, f"Failed to parse spreadsheet: {exc}") from exc

    inserted = 0
    rejected: list[dict] = []
    for idx, r in enumerate(records):
        try:
            production_date = r.get("ProductionDate")
            doc = {
                "id": new_id(),
                "created_at": now_iso(),
                "production_date": (production_date.isoformat()
                                    if hasattr(production_date, "isoformat")
                                    else production_date),
                "well_entity": r.get("Entity"),
                "tag": r.get("Tag"),
                "tipo": r.get("Tipo"),
                "bank_name": r.get("Bank"),
                "loop_name": r.get("Loop"),
                "payload": r,
            }
            await db.mpfm_records.insert_one(doc)
            inserted += 1
        except Exception as exc:
            rejected.append({"row": idx + 1, "error": str(exc)})
            logger.warning("rejected row %d: %s", idx + 1, exc)

    return {
        "filename": file.filename,
        "records_imported": inserted,
        "records_rejected": len(rejected),
        "rejected": rejected[:20],  # cap to keep response small
        "sample": records[:3],
    }


@api_router.get("/import/mpfm-records")
async def imported_records(limit: int = 100):
    docs = await db.mpfm_records.find(
        {},
        {"_id": 0, "id": 1, "created_at": 1, "production_date": 1,
         "well_entity": 1, "tag": 1, "tipo": 1, "bank_name": 1, "loop_name": 1},
    ).sort("created_at", -1).to_list(limit)
    return docs


# ==================== App wiring ====================
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
