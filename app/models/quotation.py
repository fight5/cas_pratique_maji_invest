from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models.drawing import DrawingData


class MaterialCost(BaseModel):
    matiere: str
    masse_kg: float
    prix_unitaire_kg: float
    cout_total: float


class MachiningCost(BaseModel):
    operation: str
    temps_minutes: float
    taux_horaire: float
    cout_total: float
    quantite: int = 1


class CostBreakdown(BaseModel):
    matiere: MaterialCost
    decoupe: MachiningCost
    pliage: MachiningCost
    percage: MachiningCost
    montage: MachiningCost
    sous_total_ht: float
    marge_pct: float
    montant_marge: float
    total_ht: float
    tva_pct: float = 20.0
    total_ttc: float


class QuotationRequest(BaseModel):
    drawing_data: DrawingData
    quantite: int = 1
    marge_pct: Optional[float] = None
    taux_horaire_machine: Optional[float] = None
    taux_horaire_operateur: Optional[float] = None
    client: Optional[str] = None
    reference_commande: Optional[str] = None


class QuotationResponse(BaseModel):
    id_devis: str
    date_generation: datetime = Field(default_factory=datetime.now)
    reference_piece: Optional[str] = None
    designation: Optional[str] = None
    client: Optional[str] = None
    quantite: int
    cout_unitaire_ht: float
    cout_total_ht: float
    total_ttc: float
    breakdown: CostBreakdown
    drawing_data: DrawingData
    warnings: List[str] = Field(default_factory=list)
    notes: str = ""
