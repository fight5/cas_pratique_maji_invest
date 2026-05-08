from typing import List, Optional
from pydantic import BaseModel, Field


class Hole(BaseModel):
    forme: str = "rond"
    diametre_mm: Optional[float] = None
    quantite: int = 1
    tolerance: Optional[str] = None
    position_x_mm: Optional[float] = None
    position_y_mm: Optional[float] = None


class Bend(BaseModel):
    angle_deg: float = 0.0
    rayon_mm: Optional[float] = None
    longueur_mm: Optional[float] = None
    quantite: int = 1


class BOMItem(BaseModel):
    rep: int = 0
    designation: str = ""
    quantite: int = 1
    reference: Optional[str] = None


class Dimensions(BaseModel):
    longueur_mm: Optional[float] = None
    largeur_mm: Optional[float] = None
    hauteur_mm: Optional[float] = None
    surface_depliee_mm2: Optional[float] = None
    perimetre_decoupe_mm: Optional[float] = None


class Tolerances(BaseModel):
    generales: Optional[str] = None
    specifiques: List[str] = Field(default_factory=list)


class DrawingData(BaseModel):
    nom_piece: Optional[str] = None
    reference: Optional[str] = None
    matiere: Optional[str] = None
    nuance: Optional[str] = None
    epaisseur_mm: Optional[float] = None
    masse_estimee_g: Optional[float] = None
    dimensions: Dimensions = Field(default_factory=Dimensions)
    percages: List[Hole] = Field(default_factory=list)
    pliages: List[Bend] = Field(default_factory=list)
    nomenclature: List[BOMItem] = Field(default_factory=list)
    tolerances: Tolerances = Field(default_factory=Tolerances)
    notes_techniques: List[str] = Field(default_factory=list)
    traitement_surface: Optional[str] = None
    confidence_score: float = 0.0


class OCRResult(BaseModel):
    text: str
    confidence: float
    bbox: List[float]
    is_rotated: bool = False


class ExtractionResult(BaseModel):
    ocr_raw: List[OCRResult] = Field(default_factory=list)
    drawing_data: DrawingData = Field(default_factory=DrawingData)
    processing_time_ms: int = 0
    warnings: List[str] = Field(default_factory=list)
