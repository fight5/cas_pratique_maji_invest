import json
import logging

import cv2
import numpy as np
from PIL import Image

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
- Dimensions toujours en millimetres
- Identifier chaque percage (forme, diametre, quantite, tolerance)
- Reperer tous les pliages (angle, rayon, longueur)
- Extraire la nomenclature complete (REP / DESIGNATION / QTE)
- Capturer toutes les notes techniques et tolerances
- confidence_score entre 0.0 et 1.0 selon ta certitude globale
"""


class VisionService:
    """Service Vision IA utilisant le SDK Google GenAI (Gemini Flash).

    Utilise google-genai (nouveau SDK) pour eviter les avertissements
    de deprecation du package google-generativeai.
    """

    def __init__(self):
        settings = get_settings()

        if not settings.active_api_key:
            raise ValueError(
                "Aucune cle API configuree. "
                "Ajoute GEMINI_API_KEY ou OPENAI_API_KEY dans le fichier .env"
            )

        self.use_gemini = bool(settings.gemini_api_key)
        self.api_key = settings.active_api_key
        self.model_name = settings.active_model

        if self.use_gemini:
            try:
                from google import genai
                self.genai_client = genai.Client(api_key=self.api_key)
                self._sdk = "new"
                logger.info(f"VisionService — google.genai ({self.model_name})")
            except Exception:
                import google.generativeai as genai_legacy
                genai_legacy.configure(api_key=self.api_key)
                self.gemini_model = genai_legacy.GenerativeModel(self.model_name)
                self._sdk = "legacy"
                logger.info(f"VisionService — google-generativeai legacy ({self.model_name})")
        else:
            from openai import OpenAI
            self.openai_client = OpenAI(api_key=self.api_key)
            self._sdk = "openai"
            logger.info(f"VisionService — OpenAI ({self.model_name})")

    def analyze_drawing(self, image: np.ndarray) -> DrawingData:
        if self.use_gemini:
            return self._analyze_with_gemini(image)
        return self._analyze_with_openai(image)

    def _analyze_with_gemini(self, image: np.ndarray) -> DrawingData:
        pil_image = self._cv2_to_pil(image)
        try:
            if self._sdk == "new":
                from google.genai import types
                response = self.genai_client.models.generate_content(
                    model=self.model_name,
                    contents=[EXTRACTION_PROMPT, pil_image],
                    config=types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=8192,
                    ),
                )
                raw = response.text
            else:
                response = self.gemini_model.generate_content(
                    [EXTRACTION_PROMPT, pil_image],
                    generation_config={"temperature": 0.1, "max_output_tokens": 8192},
                )
                raw = response.text
        except Exception as e:
            logger.error(f"Erreur Gemini: {e}")
            raise
        logger.debug(f"Reponse Gemini (extrait): {raw[:300]}...")
        return self._parse_response(raw)

    def _analyze_with_openai(self, image: np.ndarray) -> DrawingData:
        import base64
        _, buffer = cv2.imencode(".png", image)
        image_b64 = base64.b64encode(buffer).decode("utf-8")
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model_name,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": EXTRACTION_PROMPT},
                        {"type": "image_url", "image_url": {
                            "url": f"data:image/png;base64,{image_b64}",
                        }},
                    ],
                }],
                max_tokens=2500,
                temperature=0.1,
            )
            raw = response.choices[0].message.content
        except Exception as e:
            logger.error(f"Erreur OpenAI: {e}")
            raise
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
            logger.error(f"Parsing Vision echoue: {e}\nContenu: {content[:500]}")
            return DrawingData(confidence_score=0.0)

    @staticmethod
    def _cv2_to_pil(image: np.ndarray) -> Image.Image:
        if len(image.shape) == 2:
            return Image.fromarray(image)
        return Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
