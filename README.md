# Cas pratique MAJI — Devis automatique depuis plans techniques

Outil IA pour lire des plans techniques et générer des devis. Développé dans le cadre du cas pratique MAJI.

---

## C'est quoi ?

MAJI c'est un groupe industriel (tôlerie, composites, peinture). Les devis se font encore à la main sur Excel, c'est long et ça dépend trop d'une seule personne.

L'idée : uploader un plan PDF → l'IA extrait les infos → le devis est généré automatiquement.

---

## Comment ça marche

```
Plan technique (PDF ou image)
        │
        ▼
Prétraitement OpenCV  ← améliore la qualité pour l'OCR
        │
        ▼
OCR PaddleOCR  ← extrait le texte brut
        │
        ▼
Vision IA Gemini 2.5 Flash  ← comprend le plan, retourne un JSON structuré
        │                       (dimensions, perçages, pliages, nomenclature...)
        ▼
Fusion OCR + Vision  ← l'OCR comble ce que Gemini a raté
        │
        ▼
Calcul du devis  ← matière + laser + pliage + perçage + montage + marge
        │
        ▼
Export JSON / Excel
```

---

## Structure

```
maji-devis-ai/
├── app/
│   ├── main.py
│   ├── core/config.py
│   ├── api/routes/
│   │   ├── drawings.py       # POST /drawings/analyze
│   │   └── quotations.py     # POST /quotations/generate
│   ├── services/
│   │   ├── preprocessing.py
│   │   ├── ocr_service.py
│   │   ├── vision_service.py
│   │   ├── extraction_service.py
│   │   └── quotation_service.py
│   └── models/
│       ├── drawing.py
│       └── quotation.py
├── frontend/
│   └── streamlit_app.py
├── .streamlit/config.toml
├── .env.example
├── requirements.txt
└── docker-compose.yml
```

---

## Lancer le projet

### Prérequis

- Python 3.11+
- Une clé Gemini gratuite → https://aistudio.google.com/apikey

### Installation

```bash
git clone https://github.com/fight5/cas_pratique_maji
cd cas_pratique_maji

python -m venv venv
venv\Scripts\activate  # Windows
# ou: source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# coller la clé GEMINI_API_KEY dans .env
```

### Démarrage

```bash
# terminal 1 — API
uvicorn app.main:app --reload --port 8000

# terminal 2 — interface
streamlit run frontend/streamlit_app.py
```

- Interface : http://localhost:8501
- API docs : http://localhost:8000/docs

### Docker

```bash
docker-compose up --build
```

---

## API

### Analyser un plan
`POST /api/v1/drawings/analyze`

Upload multipart (PDF, PNG, JPG, TIFF). Retourne :

```json
{
  "drawing_data": {
    "nom_piece": "SUPPORT",
    "matiere": "Acier DC01",
    "epaisseur_mm": 2.0,
    "dimensions": { "longueur_mm": 60.0, "largeur_mm": 60.0 },
    "percages": [{ "diametre_mm": 5.5, "quantite": 4 }],
    "pliages": [{ "angle_deg": 90.0, "quantite": 2 }],
    "confidence_score": 0.9
  },
  "processing_time_ms": 57000
}
```

### Générer un devis
`POST /api/v1/quotations/generate`

```json
{
  "drawing_data": { "..." },
  "quantite": 10,
  "marge_pct": 0.30,
  "client": "Client X"
}
```

---

## Calcul des coûts

| Poste | Logique |
|---|---|
| Matière | masse × 1,15 (chute) × prix/kg |
| Découpe laser | périmètre / vitesse + setup 1,5 min |
| Pliage | 5 min setup + 0,8 min/pli |
| Perçage | 0,5 min/trou |
| Montage | 10 min + 2,5 min/composant |
| Marge | % sur sous-total (défaut 30%) |

Prix matières simulés (Acier 1,80€/kg, Inox 5,20€/kg, Alu 4,50€/kg).

---

## Ce qui manque / idées pour la suite

- [ ] Analyse multi-pages PDF
- [ ] Export PDF du devis avec entête MAJI
- [ ] Historique des devis
- [ ] Vrais prix matières (connecter un ERP ou une API)
- [ ] Fine-tuning du prompt selon le type de pièce

---

## Stack

FastAPI · Gemini 2.5 Flash · PaddleOCR · OpenCV · Streamlit · Pydantic v2 · Docker
