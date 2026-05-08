import logging
from typing import List

import numpy as np

logger = logging.getLogger(__name__)


def pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[np.ndarray]:
    """Convertit un PDF en liste d'images numpy (une par page) à la résolution donnée.

    Utilise PyMuPDF (fitz) en priorité pour la qualité et la rapidité.
    Fallback vers pdf2image si PyMuPDF est absent.
    """
    try:
        import fitz  # PyMuPDF

        return _convert_with_pymupdf(pdf_bytes, dpi)
    except ImportError:
        logger.warning("PyMuPDF absent — fallback vers pdf2image")
        return _convert_with_pdf2image(pdf_bytes, dpi)


def _convert_with_pymupdf(pdf_bytes: bytes, dpi: int) -> List[np.ndarray]:
    import cv2
    import fitz

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images = []
    zoom = dpi / 72
    mat = fitz.Matrix(zoom, zoom)

    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=mat, alpha=False)
        arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)

        if pix.n == 4:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            arr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)

        images.append(arr)
        logger.info(f"Page {i + 1}/{len(doc)} convertie: {pix.width}×{pix.height}px")

    doc.close()
    return images


def _convert_with_pdf2image(pdf_bytes: bytes, dpi: int) -> List[np.ndarray]:
    import cv2
    from pdf2image import convert_from_bytes

    pil_images = convert_from_bytes(pdf_bytes, dpi=dpi)
    result = []
    for img in pil_images:
        import numpy as np

        arr = np.array(img)
        result.append(cv2.cvtColor(arr, cv2.COLOR_RGB2BGR))
    return result
