import logging
import re
import time

import numpy as np

from app.models.drawing import DrawingData, ExtractionResult, OCRResult
from app.services.ocr_service import OCRService
from app.services.preprocessing import ImagePreprocessor
from app.services.vision_service import VisionService

logger = logging.getLogger(__name__)


class ExtractionService:
    """Orchestre le pipeline complet d'extraction sur un plan technique.

    Ordre des étapes :
    1. Prétraitement OpenCV (upscale, débruitage, CLAHE, deskew, binarisation)
    2. OCR PaddleOCR sur l'image améliorée
    3. Analyse Vision IA (GPT-4o) sur l'image couleur haute qualité
    4. Enrichissement : les résultats OCR comblent les champs manquants du Vision
    """

    def __init__(self):
        self.preprocessor = ImagePreprocessor()
        self.ocr_service = OCRService()
        self.vision_service = VisionService()

    def process_image(self, image: np.ndarray) -> ExtractionResult:
        """Pipeline principal d'extraction — retourne ExtractionResult."""
        t0 = time.time()
        warnings: list[str] = []

        # Étape 1 — prétraitement
        logger.info("[1/3] Prétraitement de l'image...")
        image_enhanced, image_bw = self.preprocessor.preprocess(image)

        # Étape 2 — OCR
        logger.info("[2/3] Extraction OCR (PaddleOCR)...")
        try:
            ocr_results = self.ocr_service.extract(image_enhanced)
        except Exception as e:
            logger.warning(f"OCR échoué (non bloquant): {e}")
            ocr_results = []
            warnings.append(f"OCR partiel: {e}")

        # Étape 3 — Vision IA
        logger.info("[3/3] Analyse Vision IA (GPT-4o)...")
        try:
            drawing_data = self.vision_service.analyze_drawing(image_enhanced)
        except Exception as e:
            logger.error(f"Vision IA échouée: {e}")
            drawing_data = self._fallback_from_ocr(ocr_results)
            warnings.append(f"Vision IA indisponible — fallback OCR: {e}")

        # Enrichissement croisé OCR ↔ Vision
        drawing_data = self._enrich_with_ocr(drawing_data, ocr_results)

        elapsed_ms = int((time.time() - t0) * 1000)
        logger.info(f"Pipeline terminé en {elapsed_ms} ms")

        return ExtractionResult(
            ocr_raw=ocr_results,
            drawing_data=drawing_data,
            processing_time_ms=elapsed_ms,
            warnings=warnings,
        )

    # ------------------------------------------------------------------
    # Méthodes privées
    # ------------------------------------------------------------------

    def _enrich_with_ocr(
        self, drawing_data: DrawingData, ocr_results: list[OCRResult]
    ) -> DrawingData:
        """Comble les champs nuls de DrawingData avec des extractions OCR ciblées."""
        if not ocr_results:
            return drawing_data

        all_text = " ".join(r.text for r in ocr_results).upper()

        # Masse (ex : "68 G", "0.068 KG")
        if drawing_data.masse_estimee_g is None:
            m = re.search(r"(\d+(?:\.\d+)?)\s*(?:G\b|GR\b|GRAMME)", all_text)
            if m:
                drawing_data.masse_estimee_g = float(m.group(1))
            else:
                m_kg = re.search(r"(\d+(?:\.\d+)?)\s*KG", all_text)
                if m_kg:
                    drawing_data.masse_estimee_g = float(m_kg.group(1)) * 1000

        # Épaisseur (ex : "EP. 2", "EPAISSEUR 2MM")
        if drawing_data.epaisseur_mm is None:
            m = re.search(r"EP(?:AISSEUR)?\s*[.:=]?\s*(\d+(?:\.\d+)?)", all_text)
            if m:
                drawing_data.epaisseur_mm = float(m.group(1))

        return drawing_data

    def _fallback_from_ocr(self, ocr_results: list[OCRResult]) -> DrawingData:
        """Extraction de secours basée uniquement sur l'OCR brut."""
        all_text = " ".join(r.text for r in ocr_results)
        data = DrawingData(confidence_score=0.25)

        dims = re.findall(r"(\d+(?:\.\d+)?)\s*mm", all_text, re.IGNORECASE)
        if dims:
            sorted_dims = sorted([float(d) for d in dims], reverse=True)
            if len(sorted_dims) >= 1:
                data.dimensions.longueur_mm = sorted_dims[0]
            if len(sorted_dims) >= 2:
                data.dimensions.largeur_mm = sorted_dims[1]
            if len(sorted_dims) >= 3:
                data.dimensions.hauteur_mm = sorted_dims[2]

        return data
