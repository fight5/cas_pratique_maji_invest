import io
import logging

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from PIL import Image

from app.models.drawing import ExtractionResult
from app.services.extraction_service import ExtractionService
from app.utils.pdf_utils import pdf_to_images

router = APIRouter(prefix="/drawings", tags=["Analyse de Plans"])
logger = logging.getLogger(__name__)

ALLOWED_TYPES = {
    "application/pdf",
    "image/png",
    "image/jpeg",
    "image/tiff",
    "image/bmp",
    "image/webp",
}


def get_extraction_service() -> ExtractionService:
    return ExtractionService()


@router.post(
    "/analyze",
    response_model=ExtractionResult,
    summary="Analyser un plan technique",
    description=(
        "Upload un plan technique (PDF, PNG, JPG, TIFF) et retourne les données "
        "structurées extraites : dimensions, percages, pliages, nomenclature, tolérances."
    ),
)
async def analyze_drawing(
    file: UploadFile = File(..., description="Plan technique (PDF, PNG, JPG, TIFF)"),
    service: ExtractionService = Depends(get_extraction_service),
) -> ExtractionResult:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Fichier vide")

    filename = (file.filename or "").lower()

    try:
        if filename.endswith(".pdf") or file.content_type == "application/pdf":
            pages = pdf_to_images(content, dpi=200)
            if not pages:
                raise HTTPException(status_code=422, detail="PDF vide ou illisible")
            image = pages[0]
        else:
            pil_img = Image.open(io.BytesIO(content)).convert("RGB")
            image = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur chargement fichier '{filename}': {e}")
        raise HTTPException(status_code=422, detail=f"Impossible de lire le fichier: {e}")

    try:
        return service.process_image(image)
    except Exception as e:
        logger.error(f"Erreur pipeline extraction: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erreur d'analyse: {e}")
