import base64
import json
import logging

import cv2
import numpy as np
from openai import OpenAI

from app.core.config import get_settings
from app.models.drawing import DrawingData

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Tu es un expert en lecture de plans techniques industriels (tôlerie, usinage, mécanique de précision).

Analyse ce plan technique et extrais TOUTES les informations disponibles.
Sois exhaustif et précis. Si une valeur est absente ou illisible, utilise null.

Retourne UNIQUEMENT un objet JSON valide, sans markdown ni commentaire :

{
  "nom_piece": null,
  "reference": null,
  "matiere": null,
  "nuance": null,
  "epaisseur_mm": null,
  "masse_estimee_g": null,
  "dimensions": {
    "longueur_mm": null,
    "largeur_mm": null,
    "hauteur_mm": null,
    "surface_depliee_mm2": null,
    "perimetre_decoupe_mm": null
  },
  "percages": [
    {
      "forme": "rond",
      "diametre_mm": null,
      "quantite": 1,
      "tolerance": null,
      "position_x_mm": null,
      "position_y_mm": null
    }
  ],
  "pliages": [
    {
      "angle_deg": null,
      "rayon_mm": null,
      "longueur_mm": null,
      "quantite": 1
    }
  ],
  "nomenclature": [
    {
      "rep": 1,
      "designation": null,
      "quantite": 1,
      "reference": null
    }
  ],
  "tolerances": {
    "generales": null,
    "specifiques": []
  },
  "notes_techniques": [],
  "traitement_surface": null,
  "confidence_score": 0.0
}

Instructions :
- Dimensions toujours en millimètres
- Identifier chaque percage (forme, diamètre, quantité, tolérance)
- Repérer tous les pliages (angle, rayon, longueur)
- Extraire la nomenclature complète (REP / DESIGNATION / QTÉ)
- Capturer toutes les notes techniques et tolérances
- confidence_score entre 0.0 et 1.0 selon ta certitude globale
"""


class VisionService:
    """Service Vision IA — compatible Gemini Flash (gratuit) et GPT-4o.

    Utilise l'API OpenAI-compatible de Google pour Gemini,
    ce qui permet de ne changer que la base_url et le modèle.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.active_api_key:
            raise ValueError(
                "Aucune clé API configurée. "
                "Ajoute GEMINI_API_KEY ou OPENAI_API_KEY dans le fichier .env"
            )

        self.client = OpenAI(
            api_key=settings.active_api_key,
            base_url=settings.active_base_url,
        )
        self.model = settings.active_model
        provider = "Gemini Flash" if settings.gemini_api_key else "GPT-4o"
        logger.info(f"VisionService initialisé — provider: {provider}, modèle: {self.model}")

    def analyze_drawing(self, image: np.ndarray) -> DrawingData:
        """Envoie le plan au modèle Vision et retourne les données structurées."""
        image_b64 = self._encode_image(image)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": EXTRACTION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{image_b64}",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=2500,
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"Erreur API Vision ({self.model}): {e}")
            raise

        raw = response.choices[0].message.content
        logger.debug(f"Réponse Vision brute (extrait): {raw[:300]}...")
        return self._parse_response(raw)

    def _parse_response(self, content: str) -> DrawingData:
        content = content.strip()
        if content.startswith("```"):
            parts = content.split("```")
            content = parts[1] if len(parts) > 1 else parts[0]
            if content.lower().startswith("json"):
                content = content[4:]
        try:
            data = json.loads(content.strip())
            return DrawingData(**data)
        except Exception as e:
            logger.error(f"Parsing réponse Vision échoué: {e}\nContenu: {content[:500]}")
            return DrawingData(confidence_score=0.0)

    @staticmethod
    def _encode_image(image: np.ndarray) -> str:
        if len(image.shape) == 2:
            image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        _, buffer = cv2.imencode(".png", image)
        return base64.b64encode(buffer).decode("utf-8")
