import logging
import math
from typing import List

import numpy as np

from app.models.drawing import OCRResult

logger = logging.getLogger(__name__)


class OCRService:
    """Service OCR basé sur PaddleOCR.

    PaddleOCR est privilégié sur Tesseract pour sa robustesse sur les textes
    pivotés, les petites polices et les annotations denses des plans techniques.
    Le modèle est chargé en lazy pour éviter d'alourdir le démarrage de l'API.
    """

    def __init__(self, lang: str = "en", confidence_threshold: float = 0.7):
        self.lang = lang
        self.confidence_threshold = confidence_threshold
        self._ocr = None

    @property
    def ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(
                use_angle_cls=True,
                lang=self.lang,
                use_gpu=False,
                show_log=False,
                enable_mkldnn=False,
            )
            logger.info("PaddleOCR chargé avec succès")
        return self._ocr

    def extract(self, image: np.ndarray) -> List[OCRResult]:
        """Extrait tout le texte d'une image numpy avec positions et confiances."""
        try:
            results = self.ocr.ocr(image, cls=True)
        except Exception as e:
            logger.error(f"Erreur PaddleOCR: {e}")
            return []

        if not results or not results[0]:
            return []

        extracted = []
        for line in results[0]:
            bbox_raw, (text, confidence) = line
            if confidence < self.confidence_threshold:
                continue

            xs = [p[0] for p in bbox_raw]
            ys = [p[1] for p in bbox_raw]
            bbox = [min(xs), min(ys), max(xs), max(ys)]

            extracted.append(
                OCRResult(
                    text=text.strip(),
                    confidence=float(confidence),
                    bbox=bbox,
                    is_rotated=self._is_rotated(bbox_raw),
                )
            )

        logger.info(
            f"OCR: {len(extracted)} éléments extraits "
            f"(seuil confiance: {self.confidence_threshold})"
        )
        return extracted

    def extract_all_text(self, image: np.ndarray) -> str:
        """Retourne tout le texte OCR sous forme de chaîne plate."""
        return " | ".join(r.text for r in self.extract(image))

    @staticmethod
    def _is_rotated(bbox_raw: list) -> bool:
        if len(bbox_raw) < 2:
            return False
        dx = bbox_raw[1][0] - bbox_raw[0][0]
        dy = bbox_raw[1][1] - bbox_raw[0][1]
        return abs(math.degrees(math.atan2(dy, dx))) > 15
