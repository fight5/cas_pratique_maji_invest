import logging
import uuid
from datetime import datetime
from typing import Optional

from app.core.config import get_settings
from app.models.drawing import DrawingData
from app.models.quotation import (
    CostBreakdown, MachiningCost, MaterialCost,
    QuotationRequest, QuotationResponse,
)

logger = logging.getLogger(__name__)

MATERIAL_DATABASE = {
    "acier": {"price_per_kg": 1.80, "density_kg_m3": 7850},
    "dc01": {"price_per_kg": 1.80, "density_kg_m3": 7850},
    "xc18": {"price_per_kg": 1.95, "density_kg_m3": 7850},
    "inox": {"price_per_kg": 5.20, "density_kg_m3": 7900},
    "304": {"price_per_kg": 5.20, "density_kg_m3": 7900},
    "316": {"price_per_kg": 6.10, "density_kg_m3": 8000},
    "aluminium": {"price_per_kg": 4.50, "density_kg_m3": 2700},
    "5052": {"price_per_kg": 4.50, "density_kg_m3": 2680},
    "6061": {"price_per_kg": 5.00, "density_kg_m3": 2700},
    "laiton": {"price_per_kg": 7.80, "density_kg_m3": 8500},
    "default": {"price_per_kg": 1.80, "density_kg_m3": 7850},
}


class QuotationService:
    def __init__(self):
        self.settings = get_settings()

    def generate_quotation(self, request: QuotationRequest) -> QuotationResponse:
        drawing = request.drawing_data
        quantite = request.quantite
        warnings = []

        marge = request.marge_pct if request.marge_pct is not None else self.settings.default_margin_rate
        taux_machine = request.taux_horaire_machine or self.settings.machine_hourly_rate
        taux_op = request.taux_horaire_operateur or self.settings.operator_hourly_rate

        mat = self._calc_material(drawing, warnings)
        cut = self._calc_cutting(drawing, taux_machine)
        bend = self._calc_bending(drawing, taux_machine)
        drill = self._calc_drilling(drawing, taux_machine)
        asm = self._calc_assembly(drawing, taux_op)

        sous_total = mat.cout_total + cut.cout_total + bend.cout_total + drill.cout_total + asm.cout_total
        montant_marge = sous_total * marge
        total_ht = sous_total + montant_marge
        total_ttc = total_ht * 1.20

        self._validate(total_ht, drawing, warnings)

        breakdown = CostBreakdown(
            matiere=mat, decoupe=cut, pliage=bend, percage=drill, montage=asm,
            sous_total_ht=round(sous_total, 4),
            marge_pct=round(marge * 100, 1),
            montant_marge=round(montant_marge, 4),
            total_ht=round(total_ht, 4),
            total_ttc=round(total_ttc, 4),
        )

        return QuotationResponse(
            id_devis=str(uuid.uuid4())[:8].upper(),
            date_generation=datetime.now(),
            reference_piece=drawing.reference,
            designation=drawing.nom_piece,
            client=request.client,
            quantite=quantite,
            cout_unitaire_ht=round(total_ht, 4),
            cout_total_ht=round(total_ht * quantite, 4),
            total_ttc=round(total_ttc * quantite, 4),
            breakdown=breakdown,
            drawing_data=drawing,
            warnings=warnings,
        )

    def _calc_material(self, drawing: DrawingData, warnings: list) -> MaterialCost:
        params = self._material_params(drawing.matiere)
        masse_kg = (drawing.masse_estimee_g or 0) / 1000
        if masse_kg == 0 and drawing.dimensions.surface_depliee_mm2 and drawing.epaisseur_mm:
            surface_m2 = drawing.dimensions.surface_depliee_mm2 / 1_000_000
            masse_kg = surface_m2 * (drawing.epaisseur_mm / 1000) * params["density_kg_m3"]
        if masse_kg == 0:
            masse_kg = 0.1
            warnings.append("Masse non calculable — valeur minimale utilisée (100 g)")
        masse_avec_chute = masse_kg * 1.15
        return MaterialCost(
            matiere=drawing.matiere or "Acier DC01 (défaut)",
            masse_kg=round(masse_avec_chute, 4),
            prix_unitaire_kg=params["price_per_kg"],
            cout_total=round(masse_avec_chute * params["price_per_kg"], 4),
        )

    def _calc_cutting(self, drawing: DrawingData, taux: float) -> MachiningCost:
        perimetre = drawing.dimensions.perimetre_decoupe_mm or 400
        temps = perimetre / 3000 + 1.5
        return MachiningCost(operation="Découpe laser", temps_minutes=round(temps, 2),
                             taux_horaire=taux, cout_total=round((temps / 60) * taux, 4))

    def _calc_bending(self, drawing: DrawingData, taux: float) -> MachiningCost:
        nb = sum(p.quantite for p in drawing.pliages) if drawing.pliages else 0
        temps = (5.0 + nb * 0.8) if nb > 0 else 0
        return MachiningCost(operation="Pliage", temps_minutes=round(temps, 2),
                             taux_horaire=taux, cout_total=round((temps / 60) * taux, 4), quantite=nb)

    def _calc_drilling(self, drawing: DrawingData, taux: float) -> MachiningCost:
        nb = sum(p.quantite for p in drawing.percages) if drawing.percages else 0
        temps = nb * 0.5
        return MachiningCost(operation="Perçage", temps_minutes=round(temps, 2),
                             taux_horaire=taux, cout_total=round((temps / 60) * taux, 4), quantite=nb)

    def _calc_assembly(self, drawing: DrawingData, taux: float) -> MachiningCost:
        nb = sum(i.quantite for i in drawing.nomenclature) if drawing.nomenclature else 0
        temps = 10.0 + nb * 2.5
        return MachiningCost(operation="Montage / Finition", temps_minutes=round(temps, 2),
                             taux_horaire=taux, cout_total=round((temps / 60) * taux, 4), quantite=nb)

    def _material_params(self, matiere: Optional[str]) -> dict:
        if not matiere:
            return MATERIAL_DATABASE["default"]
        ml = matiere.lower()
        for key, val in MATERIAL_DATABASE.items():
            if key in ml:
                return val
        return MATERIAL_DATABASE["default"]

    def _validate(self, total_ht: float, drawing: DrawingData, warnings: list) -> None:
        if total_ht < 1.0:
            warnings.append("Coût total très bas — vérifier les données extraites")
        if total_ht > 5000:
            warnings.append("Coût total élevé — vérifier les dimensions")
        if drawing.confidence_score < 0.5:
            warnings.append(f"Confiance d'extraction faible ({drawing.confidence_score:.0%}) — à valider manuellement")
