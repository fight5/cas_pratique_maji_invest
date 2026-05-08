import logging

from fastapi import APIRouter, Depends, HTTPException

from app.models.quotation import QuotationRequest, QuotationResponse
from app.services.quotation_service import MATERIAL_DATABASE, QuotationService

router = APIRouter(prefix="/quotations", tags=["Génération de Devis"])
logger = logging.getLogger(__name__)


def get_quotation_service() -> QuotationService:
    return QuotationService()


@router.post(
    "/generate",
    response_model=QuotationResponse,
    summary="Générer un devis",
    description=(
        "Calcule un devis complet à partir des données extraites d'un plan technique. "
        "Décompose les coûts en: matière, découpe laser, pliage, perçage, montage + marge."
    ),
)
async def generate_quotation(
    request: QuotationRequest,
    service: QuotationService = Depends(get_quotation_service),
) -> QuotationResponse:
    try:
        return service.generate_quotation(request)
    except Exception as e:
        logger.error(f"Erreur génération devis: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/material-prices",
    summary="Consulter les prix matières",
    description="Retourne la base de données des prix et densités utilisée dans les calculs.",
)
async def get_material_prices() -> dict:
    return {k: v for k, v in MATERIAL_DATABASE.items() if k != "default"}
