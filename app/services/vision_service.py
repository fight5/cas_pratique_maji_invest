import base64
import json
import logging

import cv2
import numpy as np
from openai import OpenAI

from app.core.config import get_settings
from app.models.drawing import DrawingData

logger = logging.getLogger(__name__)

# Prompt d'extraction structurée — conçu pour les plans techniques industriels
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

Instructions importantes :
- Les dimensions sont TOUJOURS en millimètres
- Identifie chaque percage individuellement (forme, diamètre, quantité, position si visible)
- Repère tous les pliages avec leurs angles et rayons
- Extrait la nomenclature complète (tableau REP/DESIGNATION/QTÉ)
- Capture TOUTES les notes techniques et tolérances
- Le confidence_score doit refléter ta certitude globale (0.0 à 1.0)
"""


class VisionService:
    """Service d'analyse Vision IA via GPT-4o pour plans techniques industriels.

    GPT-4o en mode 'high detail' est utilisé pour sa capacité à comprendre
    la structure globale d'un plan (cartouche, vues, nomenclature, cotations)
    que l'OCR seul ne peut pas contextualiser.
    """

    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        logger.info(f"VisionService initialisé — modèle: {self.model}")

    def analyze_drawing(self, image: np.ndarray) -> DrawingData:
        """Envoie le plan à GPT-4o et retourne les données structurées."""
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
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=2500,
                temperature=0.1,
            )
        except Exception as e:
            logger.error(f"Erreur API OpenAI Vision: {e}")
            raise

        raw = response.choices[0].message.content
        logger.debug(f"Réponse Vision (extrait): {raw[:300]}...")
        return self._parse_response(raw)

    def _parse_response(self, content: str) -> DrawingData:
        content = content.strip()
        # Nettoyer les balises markdown éventuelles
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
