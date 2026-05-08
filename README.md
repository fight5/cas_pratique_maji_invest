# MAJI — Analyse de Plans Techniques & Génération de Devis

> Outil IA industriel pour l'extraction automatique d'informations depuis des plans techniques et la génération de devis structurés.

---

## Contexte métier

MAJI est un groupe industriel français (235 collaborateurs, 7 sites) spécialisé en tôlerie, composites et peinture industrielle. Actuellement, les devis sont créés manuellement en Excel — processus long, peu fiable, dépendant de multiples sources.

Cet outil automatise le pipeline **plan technique → extraction → devis**, en combinant prétraitement d'image, OCR avancé et Vision IA multimodale.

---

## Architecture

```
Plan technique (PDF / Image)
        │
        ▼
[1] Prétraitement OpenCV
    Upscale → Débruitage → CLAHE → Deskewing → Binarisation
        │
        ▼
[2] OCR — PaddleOCR
    Extraction texte + bounding boxes (texte pivoté supporté)
        │
        ▼
[3] Vision IA — Gemini 2.0 Flash
    Compréhension structurelle du plan
    → JSON : dimensions, percages, pliages, nomenclature, tolérances
        │
        ▼
[4] Fusion & enrichissement croisé
    OCR comble les champs manquants de la Vision
        │
        ▼
[5] Moteur de devis
    Matière + Découpe laser + Pliage + Perçage + Montage + Marge
        │
        ▼
[6] Export
    JSON structuré · Excel · API REST
```

---

## Structure du projet

```
maji-devis-ai/
├── app/
│   ├── main.py                      # Point d'entrée FastAPI
│   ├── core/
│   │   └── config.py                # Configuration (Pydantic Settings)
│   ├── api/
│   │   └── routes/
│   │       ├── drawings.py          # Route POST /drawings/analyze
│   │       └── quotations.py        # Route POST /quotations/generate
│   ├── services/
│   │   ├── preprocessing.py         # Pipeline OpenCV
│   │   ├── ocr_service.py           # Wrapper PaddleOCR
│   │   ├── vision_service.py        # Client Gemini Flash Vision
│   │   ├── extraction_service.py    # Orchestration pipeline
│   │   └── quotation_service.py     # Moteur de calcul de devis
│   ├── models/
│   │   ├── drawing.py               # Modèles Pydantic plan technique
│   │   └── quotation.py             # Modèles Pydantic devis
│   └── utils/
│       └── pdf_utils.py             # Conversion PDF → images
├── frontend/
│   └── streamlit_app.py             # Interface utilisateur Streamlit
├── tests/
│   └── test_pipeline.py             # Tests unitaires (sans API)
├── sample_data/                     # Plans techniques exemples
├── .env.example                     # Variables d'environnement
├── requirements.txt
├── Dockerfile
├── Dockerfile.frontend
└── docker-compose.yml
```

---

## Installation

### Prérequis

- Python 3.11+
- Clé API **Google Gemini** (gratuit) → [aistudio.google.com/apikey](https://aistudio.google.com/apikey)
- Ou clé API OpenAI (GPT-4o, payant)

### Installation locale

```bash
# Cloner le projet
git clone <repo-url>
cd maji-devis-ai

# Environnement virtuel
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Dépendances
pip install -r requirements.txt

# Configuration
cp .env.example .env
# → Renseigner GEMINI_API_KEY (gratuit) ou OPENAI_API_KEY dans .env
```

### Lancement

```bash
# API backend
uvicorn app.main:app --reload --port 8000

# Frontend (dans un autre terminal)
streamlit run frontend/streamlit_app.py
```

### Avec Docker

```bash
docker-compose up --build
```

Accès :
- API : http://localhost:8000
- Swagger : http://localhost:8000/docs
- Interface : http://localhost:8501

---

## API Reference

### `POST /api/v1/drawings/analyze`

Upload et analyse un plan technique.

**Corps** : `multipart/form-data` avec le fichier (`PDF`, `PNG`, `JPG`, `TIFF`)

**Réponse** : `ExtractionResult`
```json
{
  "ocr_raw": [...],
  "drawing_data": {
    "nom_piece": "SUPPORT REAR BRAKE",
    "reference": "PIECE_003",
    "matiere": "Acier DC01",
    "epaisseur_mm": 2.0,
    "masse_estimee_g": 68.0,
    "dimensions": {
      "longueur_mm": 60.0,
      "largeur_mm": 50.0,
      "surface_depliee_mm2": 8667.4
    },
    "percages": [{"forme": "rond", "diametre_mm": 8.75, "quantite": 2}],
    "pliages": [{"angle_deg": 45.0, "rayon_mm": 2.0, "quantite": 2}],
    "nomenclature": [...],
    "notes_techniques": ["RAYON DE PLIAGE: 2mm"],
    "confidence_score": 0.92
  },
  "processing_time_ms": 8200,
  "warnings": []
}
```

---

### `POST /api/v1/quotations/generate`

Génère un devis à partir des données extraites.

**Corps** :
```json
{
  "drawing_data": { ... },
  "quantite": 10,
  "marge_pct": 0.30,
  "client": "Airbus Group"
}
```

**Réponse** : `QuotationResponse`
```json
{
  "id_devis": "A3F8C2D1",
  "date_generation": "2026-05-08T14:30:00",
  "cout_unitaire_ht": 24.85,
  "cout_total_ht": 248.50,
  "total_ttc": 298.20,
  "breakdown": {
    "matiere": {"cout_total": 0.14},
    "decoupe": {"temps_minutes": 1.64, "cout_total": 2.32},
    "pliage": {"temps_minutes": 6.6, "cout_total": 9.35},
    "percage": {"temps_minutes": 1.0, "cout_total": 1.42},
    "montage": {"temps_minutes": 17.5, "cout_total": 10.21},
    "sous_total_ht": 23.44,
    "marge_pct": 30.0,
    "total_ht": 30.47,
    "total_ttc": 36.57
  }
}
```

---

## Logique métier — Calcul des coûts

| Poste | Méthode de calcul | Paramètres |
|---|---|---|
| **Matière** | masse × 1,15 (chute) × prix/kg | Prix par matière (base simulée) |
| **Découpe laser** | périmètre / vitesse_laser + setup | Vitesse 3000 mm/min, setup 1,5 min |
| **Pliage** | setup 5 min + 0,8 min/pli | Taux machine configurable |
| **Perçage** | 0,5 min/trou | Taux machine configurable |
| **Montage** | 10 min + 2,5 min/composant | Taux opérateur configurable |
| **Marge** | % appliqué sur le sous-total | Défaut: 30%, modifiable |

### Base de prix matières (simulée)

| Matière | Prix (€/kg) | Densité (kg/m³) |
|---|---|---|
| Acier DC01 | 1,80 | 7850 |
| Inox 304 | 5,20 | 7900 |
| Aluminium 5052 | 4,50 | 2680 |
| Laiton | 7,80 | 8500 |

---

## Fiabilité & Détection d'erreurs

- **Score de confiance** : chaque extraction Vision retourne un `confidence_score` (0–1). En dessous de 0,5, un avertissement est injecté dans le devis.
- **Validation des coûts** : alertes si le total est < 1 € ou > 5 000 €.
- **Fallback OCR** : si l'API Vision est indisponible, l'extraction tente une inférence sur l'OCR brut.
- **Enrichissement croisé** : les champs manquants du résultat Vision sont complétés par des patterns regex sur l'OCR.

---

## Tests

```bash
pytest tests/ -v
```

Les tests unitaires ne nécessitent pas de clé API — ils mockent les couches Vision et OCR.

---

## Évolutions prévues

- [ ] Support multi-pages PDF (analyse de chaque vue)
- [ ] Détection et surlignage des zones annotées (OpenCV contours)
- [ ] Export PDF du devis avec cartouche MAJI
- [ ] Base de données persistante des prix matières
- [ ] Historique des devis avec filtrage
- [ ] Support multilingue (plans FR/EN/DE)
- [ ] Fine-tuning prompt selon le type de pièce (tôle, usinage, composite)

---

## Stack technique

| Couche | Technologie |
|---|---|
| API Backend | FastAPI + Uvicorn |
| Vision IA | Google Gemini 2.0 Flash (natif) / OpenAI GPT-4o (alternatif) |
| OCR | PaddleOCR (angle_cls activé) |
| Prétraitement | OpenCV + NumPy + Pillow |
| PDF | PyMuPDF (fitz) |
| Validation | Pydantic v2 |
| Interface | Streamlit |
| Export | Pandas + openpyxl |
| Conteneurisation | Docker + Docker Compose |
