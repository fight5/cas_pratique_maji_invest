import base64
import logging
import math
from typing import Tuple

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Pipeline de prétraitement d'images pour plans techniques industriels.

    Enchaîne : upscale → débruitage → amélioration contraste → deskewing → binarisation.
    Retourne deux versions : couleur (pour la Vision IA) et N&B (pour l'OCR).
    """

    def __init__(self, min_size: int = 1500):
        self.min_size = min_size

    def preprocess(self, image: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Applique le pipeline complet et retourne (image_couleur, image_bw_ocr)."""
        image = self._upscale_if_needed(image)
        image = self._denoise(image)
        image_enhanced = self._enhance_contrast(image)
        image_enhanced = self._deskew(image_enhanced)
        image_bw = self._binarize(image_enhanced)
        return image_enhanced, image_bw

    def _upscale_if_needed(self, image: np.ndarray) -> np.ndarray:
        h, w = image.shape[:2]
        if min(h, w) < self.min_size:
            scale = self.min_size / min(h, w)
            new_w, new_h = int(w * scale), int(h * scale)
            image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
            logger.info(f"Image upscalée: {w}×{h} → {new_w}×{new_h}")
        return image

    def _denoise(self, image: np.ndarray) -> np.ndarray:
        if len(image.shape) == 3:
            return cv2.fastNlMeansDenoisingColored(
                image, None, h=6, hColor=6, templateWindowSize=7, searchWindowSize=21
            )
        return cv2.fastNlMeansDenoising(
            image, None, h=10, templateWindowSize=7, searchWindowSize=21
        )

    def _enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Amélioration adaptative du contraste via CLAHE (espace LAB)."""
        if len(image.shape) == 3:
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            l = clahe.apply(l)
            lab = cv2.merge([l, a, b])
            return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)

    def _deskew(self, image: np.ndarray) -> np.ndarray:
        """Corrige l'inclinaison du document si elle est inférieure à 10°."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(binary > 0))

        if len(coords) < 100:
            return image

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = 90 + angle

        if 0.5 < abs(angle) < 10:
            h, w = image.shape[:2]
            M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
            image = cv2.warpAffine(
                image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
            )
            logger.info(f"Deskewing: correction de {angle:.2f}°")
        return image

    def _binarize(self, image: np.ndarray) -> np.ndarray:
        """Binarisation adaptative Gaussienne — optimale pour les plans techniques."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        return cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 15, 8
        )

    @staticmethod
    def pil_to_cv2(pil_image: Image.Image) -> np.ndarray:
        return cv2.cvtColor(np.array(pil_image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def cv2_to_pil(cv2_image: np.ndarray) -> Image.Image:
        if len(cv2_image.shape) == 3:
            return Image.fromarray(cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB))
        return Image.fromarray(cv2_image)

    @staticmethod
    def encode_to_base64(image: np.ndarray) -> str:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        _, buffer = cv2.imencode(".png", image)
        return base64.b64encode(buffer).decode("utf-8")
