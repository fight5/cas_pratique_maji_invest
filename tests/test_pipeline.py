"""
Tests unitaires du pipeline d'extraction et de génération de devis.
Utilisés sans clé API (les services Vision sont mockés).
"""

import numpy as np
import pytest

from app.models.drawing import Bend, DrawingData, Hole, BOMItem, Dimensions
from app.services.preprocessing import ImagePreprocessor
from app.services.quotation_service import QuotationService
from app.models.quotation import QuotationRequest


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def sample_image() -> np.ndarray:
    """Image synthétique blanc pur 800×600."""
    return np.ones((600, 800, 3), dtype=np.uint8) * 255


@pytest.fixture
def support_rear_brake() -> DrawingData:
    """Données simulant l'extraction du plan piece_003 (SUPPORT REAR BRAKE)."""
    return DrawingData(
        nom_piece="SUPPORT REAR BRAKE",
        reference="PIECE_003",
        matiere="Acier DC01",
        epaisseur_mm=2.0,
        masse_estimee_g=68.0,
        dimensions=Dimensions(
            longueur_mm=60.0,
            largeur_mm=50.0,
            hauteur_mm=42.0,
            surface_depliee_mm2=8667.4,
            perimetre_decoupe_mm=420.0,
        ),
        percages=[
            Hole(forme="rond", diametre_mm=8.75, quantite=2, tolerance="0.1"),
        ],
        pliages=[
            Bend(angle_deg=45.0, rayon_mm=2.0, longueur_mm=50.0, quantite=2),
        ],
        nomenclature=[
            BOMItem(rep=1, designation="SUPPORT", quantite=1),
            BOMItem(rep=2, designation="ECROU A SERTIR M6 CL6", quantite=2),
        ],
        notes_techniques=[
            "RAYON DE PLIAGE: 2mm",
            "RAYONS NON COTES: 2mm",
            "EPARGNE PEINTURE DES FILETAGES",
        ],
        confidence_score=0.92,
    )


# ── Tests prétraitement ────────────────────────────────────────────────────────

class TestImagePreprocessor:
    def test_preprocess_returns_two_images(self, sample_image):
        proc = ImagePreprocessor()
        enhanced, bw = proc.preprocess(sample_image)
        assert enhanced.shape[:2] == bw.shape[:2]
        assert len(bw.shape) == 2  # N&B = 2 dimensions

    def test_upscale_small_image(self):
        small = np.ones((300, 400, 3), dtype=np.uint8) * 200
        proc = ImagePreprocessor(min_size=1500)
        upscaled = proc._upscale_if_needed(small)
        assert min(upscaled.shape[:2]) >= 1500

    def test_encode_to_base64(self, sample_image):
        b64 = ImagePreprocessor.encode_to_base64(sample_image)
        assert isinstance(b64, str)
        assert len(b64) > 0


# ── Tests calcul de devis ──────────────────────────────────────────────────────

class TestQuotationService:
    def setup_method(self):
        self.service = QuotationService()

    def test_generate_basic_quotation(self, support_rear_brake):
        req = QuotationRequest(drawing_data=support_rear_brake, quantite=1)
        result = self.service.generate_quotation(req)

        assert result.cout_unitaire_ht > 0
        assert result.total_ttc > result.cout_unitaire_ht  # TVA appliquée
        assert result.breakdown.matiere.cout_total > 0
        assert result.breakdown.decoupe.cout_total > 0

    def test_margin_applied_correctly(self, support_rear_brake):
        req = QuotationRequest(drawing_data=support_rear_brake, quantite=1, marge_pct=0.30)
        result = self.service.generate_quotation(req)
        bd = result.breakdown

        expected_total = bd.sous_total_ht * (1 + 0.30)
        assert abs(bd.total_ht - expected_total) < 0.01

    def test_quantity_multiplier(self, support_rear_brake):
        req_1 = QuotationRequest(drawing_data=support_rear_brake, quantite=1)
        req_5 = QuotationRequest(drawing_data=support_rear_brake, quantite=5)

        r1 = self.service.generate_quotation(req_1)
        r5 = self.service.generate_quotation(req_5)

        assert abs(r5.cout_total_ht - r1.cout_total_ht * 5) < 0.01

    def test_material_cost_uses_mass(self, support_rear_brake):
        req = QuotationRequest(drawing_data=support_rear_brake)
        result = self.service.generate_quotation(req)
        mat = result.breakdown.matiere

        # masse 68g × 1.15 chute × 1.80 €/kg = 0.140 €
        expected = 0.068 * 1.15 * 1.80
        assert abs(mat.cout_total - expected) < 0.05

    def test_low_confidence_warning(self, support_rear_brake):
        support_rear_brake.confidence_score = 0.3
        req = QuotationRequest(drawing_data=support_rear_brake)
        result = self.service.generate_quotation(req)
        assert any("confiance" in w.lower() for w in result.warnings)

    def test_unknown_material_uses_default(self):
        drawing = DrawingData(
            nom_piece="Pièce test",
            matiere="Titane Grade 5",
            masse_estimee_g=50.0,
            confidence_score=0.8,
        )
        req = QuotationRequest(drawing_data=drawing)
        result = self.service.generate_quotation(req)
        # Ne doit pas lever d'exception — utilise le prix acier par défaut
        assert result.cout_unitaire_ht > 0
