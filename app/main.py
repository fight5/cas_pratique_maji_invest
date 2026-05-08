import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import drawings, quotations
from app.core.config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Démarrage — {settings.app_name} v1.0.0")
    yield
    logger.info("Arrêt de l'application")


app = FastAPI(
    title="MAJI — Analyse de Plans Techniques & Génération de Devis",
    description="""
## API intelligente pour l'industrie

Outil assisté IA destiné à automatiser la lecture de plans techniques et la génération de devis
dans un contexte industriel (tôlerie, usinage, composites).

### Pipeline d'analyse
1. **Prétraitement** — OpenCV : débruitage, CLAHE, deskewing, upscale
2. **OCR** — PaddleOCR avec détection de texte pivoté
3. **Vision IA** — GPT-4o en mode haute résolution
4. **Extraction structurée** — Dimensions, percages, pliages, nomenclature, tolérances

### Génération de devis
Calcul automatique des coûts : matière, découpe laser, pliage, perçage, montage + marge.
""",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(drawings.router, prefix="/api/v1")
app.include_router(quotations.router, prefix="/api/v1")


@app.get("/", tags=["Santé"], summary="Statut de l'API")
async def root() -> dict:
    return {
        "status": "ok",
        "service": "MAJI — Analyse Plans Techniques",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", tags=["Santé"], summary="Health check")
async def health() -> dict:
    return {"status": "healthy"}
