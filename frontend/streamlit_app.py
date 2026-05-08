"""
Interface MAJI — Analyse de Plans Techniques & Génération de Devis
"""

import base64
import io
import json
import os
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from PIL import Image

API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="MAJI — Analyse Plans & Devis",
    page_icon="⚙",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand CSS ──────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;900&display=swap');

/* Global */
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Dark sidebar */
[data-testid="stSidebar"] {
    background: #0A1628 !important;
}
[data-testid="stSidebar"] * { color: #C8D6E5 !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #FFFFFF !important; }
[data-testid="stSidebar"] .stSlider > div > div > div { background: #E8420A !important; }

/* Header */
.maji-header {
    display: flex;
    align-items: center;
    gap: 2rem;
    background: linear-gradient(135deg, #0A1628 0%, #112240 60%, #1A3055 100%);
    padding: 1.5rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    border-left: 5px solid #E8420A;
}
.maji-header-text h1 {
    color: #FFFFFF;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 0 0 0.3rem 0;
    letter-spacing: 0.02em;
}
.maji-header-text p {
    color: #9EADBD;
    font-size: 0.88rem;
    margin: 0;
    letter-spacing: 0.06em;
    text-transform: uppercase;
}
.maji-wordmark {
    font-size: 3rem;
    font-weight: 900;
    color: #FFFFFF;
    letter-spacing: -1px;
    line-height: 1;
    border-left: 5px solid #E8420A;
    padding-left: 0.6rem;
}
.maji-wordmark span { color: #E8420A; }

/* Metric cards */
[data-testid="metric-container"] {
    background: #F4F7FA;
    border: 1px solid #DDE4ED;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    border-top: 3px solid #E8420A;
}

/* Primary button */
.stButton > button[kind="primary"] {
    background: #E8420A !important;
    border: none !important;
    color: white !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}
.stButton > button[kind="primary"]:hover {
    background: #C93A09 !important;
}

/* Tab styling */
[data-testid="stTabs"] button {
    font-weight: 600;
    letter-spacing: 0.03em;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: #E8420A !important;
    border-bottom-color: #E8420A !important;
}

/* Divider accent */
hr { border-color: #DDE4ED; }

/* Section headers */
h4 { color: #112240; border-bottom: 2px solid #E8420A; padding-bottom: 4px; display: inline-block; }
</style>
""", unsafe_allow_html=True)


def _load_logo_b64() -> str:
    logo_path = Path(__file__).parent / "assets" / "maji_logo.svg"
    if logo_path.exists():
        return base64.b64encode(logo_path.read_bytes()).decode()
    return ""


logo_b64 = _load_logo_b64()
logo_img_tag = (
    f'<img src="data:image/svg+xml;base64,{logo_b64}" height="70" alt="MAJI"/>'
    if logo_b64 else '<div class="maji-wordmark">MA<span>J</span>I</div>'
)

st.markdown(f"""
<div class="maji-header">
    {logo_img_tag}
    <div class="maji-header-text">
        <h1>Analyse de Plans Techniques</h1>
        <p>Extraction intelligente · Génération automatique de devis · Tôlerie &amp; Usinage</p>
    </div>
</div>
""", unsafe_allow_html=True)


def call_analyze(file_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/drawings/analyze",
        files={"file": (filename, file_bytes, _content_type(filename))},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def call_generate_quotation(payload: dict) -> dict:
    resp = requests.post(f"{API_BASE}/quotations/generate", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _content_type(filename: str) -> str:
    return {".pdf": "application/pdf", ".png": "image/png",
            ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".tiff": "image/tiff"
            }.get(Path(filename).suffix.lower(), "application/octet-stream")


def fmt_eur(value: float) -> str:
    return f"{value:.4f} €"


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Paramètres")
    st.divider()

    st.markdown("**Devis**")
    quantite = st.number_input("Quantité", min_value=1, value=1, step=1)
    marge_pct = st.slider("Marge commerciale (%)", 0, 80, 30, step=5) / 100
    client = st.text_input("Client", placeholder="Ex: Airbus Group")

    st.divider()
    st.markdown("**Tarifs (€/h)**")
    taux_machine = st.number_input("Taux machine", value=85.0, step=5.0)
    taux_operateur = st.number_input("Taux opérateur", value=35.0, step=5.0)

    st.divider()
    try:
        r = requests.get(f"{API_BASE.replace('/api/v1', '')}/health", timeout=3)
        if r.status_code == 200:
            st.success("API connectée")
        else:
            st.warning("API non disponible")
    except Exception:
        st.error("API inaccessible")


# ── Onglets ────────────────────────────────────────────────────────────────────
tab_upload, tab_results, tab_quotation, tab_export = st.tabs(
    ["Upload", "Analyse", "Devis", "Export"]
)

# ── Tab Upload ─────────────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Importer un plan technique")

    col_drop, col_info = st.columns([2, 1])

    with col_drop:
        uploaded_file = st.file_uploader(
            "Déposez votre plan ici",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
        )

        if uploaded_file:
            st.session_state["uploaded_filename"] = uploaded_file.name
            st.session_state["uploaded_bytes"] = uploaded_file.read()

            if uploaded_file.name.lower().endswith(".pdf"):
                st.info(f"PDF chargé : **{uploaded_file.name}**")
            else:
                try:
                    img = Image.open(io.BytesIO(st.session_state["uploaded_bytes"]))
                    st.image(img, caption=uploaded_file.name, use_container_width=True)
                except Exception:
                    st.warning("Prévisualisation impossible")

    with col_info:
        st.markdown("""
**Formats acceptés**
- PDF (1ère page analysée)
- PNG, JPEG, TIFF, BMP
""")

    st.divider()

    if st.session_state.get("uploaded_bytes"):
        col_btn, col_info2 = st.columns([1, 3])
        with col_btn:
            analyze_btn = st.button("Lancer l'analyse", type="primary", use_container_width=True)
        with col_info2:
            st.caption("L'analyse prend 10–30 secondes selon la complexité du plan.")

        if analyze_btn:
            with st.spinner("Analyse en cours — Prétraitement → OCR → Vision IA Gemini…"):
                try:
                    result = call_analyze(
                        st.session_state["uploaded_bytes"],
                        st.session_state["uploaded_filename"],
                    )
                    st.session_state["extraction_result"] = result
                    ocr_count = len(result.get("ocr_raw", []))
                    elapsed = result.get("processing_time_ms", 0)
                    st.success(f"Analyse terminée en {elapsed} ms — {ocr_count} éléments OCR détectés")

                    for w in result.get("warnings", []):
                        st.warning(w)

                    st.info("Consultez l'onglet **Analyse** pour les résultats détaillés")

                except requests.HTTPError as e:
                    st.error(f"Erreur API ({e.response.status_code}): {e.response.text}")
                except Exception as e:
                    st.error(f"Erreur: {e}")

# ── Tab Analyse ────────────────────────────────────────────────────────────────
with tab_results:
    if "extraction_result" not in st.session_state:
        st.info("Uploadez un plan et lancez l'analyse pour voir les résultats.")
        st.stop()

    result = st.session_state["extraction_result"]
    drawing = result.get("drawing_data", {})
    dims = drawing.get("dimensions", {})
    ocr_items = result.get("ocr_raw", [])

    st.subheader("Données extraites du plan")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confiance IA", f"{drawing.get('confidence_score', 0):.0%}")
    col2.metric("Éléments OCR", len(ocr_items))
    col3.metric("Perçages", len(drawing.get("percages", [])))
    col4.metric("Pliages", len(drawing.get("pliages", [])))

    st.divider()

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### Identification de la pièce")
        for label, key in [
            ("Nom / Désignation", "nom_piece"),
            ("Référence", "reference"),
            ("Matière", "matiere"),
            ("Nuance", "nuance"),
            ("Épaisseur (mm)", "epaisseur_mm"),
            ("Masse estimée (g)", "masse_estimee_g"),
            ("Traitement surface", "traitement_surface"),
        ]:
            st.markdown(f"**{label}** : {drawing.get(key) or '—'}")

    with col_right:
        st.markdown("#### Dimensions")
        for label, key in [
            ("Longueur (mm)", "longueur_mm"),
            ("Largeur (mm)", "largeur_mm"),
            ("Hauteur (mm)", "hauteur_mm"),
            ("Surface dépliée (mm²)", "surface_depliee_mm2"),
            ("Périmètre découpe (mm)", "perimetre_decoupe_mm"),
        ]:
            st.markdown(f"**{label}** : {dims.get(key) or '—'}")

    st.divider()

    percages = drawing.get("percages", [])
    if percages:
        st.markdown("#### Perçages")
        st.dataframe(pd.DataFrame(percages), use_container_width=True, hide_index=True)

    pliages = drawing.get("pliages", [])
    if pliages:
        st.markdown("#### Pliages")
        st.dataframe(pd.DataFrame(pliages), use_container_width=True, hide_index=True)

    nomenclature = drawing.get("nomenclature", [])
    if nomenclature:
        st.markdown("#### Nomenclature (BOM)")
        st.dataframe(pd.DataFrame(nomenclature), use_container_width=True, hide_index=True)

    col_tol, col_notes = st.columns(2)
    with col_tol:
        tol = drawing.get("tolerances", {})
        st.markdown("#### Tolérances")
        st.markdown(f"**Générales** : {tol.get('generales') or '—'}")
        for spec in tol.get("specifiques", []):
            st.markdown(f"- {spec}")

    with col_notes:
        st.markdown("#### Notes techniques")
        for note in drawing.get("notes_techniques", []):
            st.markdown(f"- {note}")

    with st.expander(f"Textes OCR bruts ({len(ocr_items)} éléments)"):
        if ocr_items:
            df_ocr = pd.DataFrame(ocr_items)[["text", "confidence", "is_rotated"]]
            df_ocr["confidence"] = df_ocr["confidence"].map(lambda x: f"{x:.1%}")
            st.dataframe(df_ocr, use_container_width=True, hide_index=True)

    with st.expander("JSON complet"):
        st.json(result)

# ── Tab Devis ──────────────────────────────────────────────────────────────────
with tab_quotation:
    if "extraction_result" not in st.session_state:
        st.info("Analysez d'abord un plan pour générer un devis.")
        st.stop()

    drawing_data = st.session_state["extraction_result"]["drawing_data"]

    st.subheader("Génération du devis")
    st.caption("Les coûts sont calculés à partir des données extraites du plan.")

    if st.button("Calculer le devis", type="primary"):
        payload = {
            "drawing_data": drawing_data,
            "quantite": quantite,
            "marge_pct": marge_pct,
            "taux_horaire_machine": taux_machine,
            "taux_horaire_operateur": taux_operateur,
            "client": client or None,
        }
        with st.spinner("Calcul en cours…"):
            try:
                st.session_state["quotation"] = call_generate_quotation(payload)
            except Exception as e:
                st.error(f"Erreur: {e}")
                st.stop()

    if "quotation" not in st.session_state:
        st.stop()

    q = st.session_state["quotation"]
    bd = q["breakdown"]

    st.divider()
    col_id, col_date, col_ref = st.columns(3)
    col_id.metric("N° Devis", q["id_devis"])
    col_date.metric("Date", q["date_generation"][:10])
    col_ref.metric("Référence", q.get("reference_piece") or "—")

    if q.get("client"):
        st.markdown(f"**Client** : {q['client']}")

    st.divider()
    st.markdown("#### Décomposition des coûts")

    rows = [
        {"Poste": "Matière",          "Détail": f"{bd['matiere']['masse_kg']} kg × {bd['matiere']['prix_unitaire_kg']} €/kg",               "Temps (min)": "—",                               "Coût HT": fmt_eur(bd["matiere"]["cout_total"])},
        {"Poste": "Découpe laser",    "Détail": f"{bd['decoupe']['taux_horaire']} €/h",                                                      "Temps (min)": str(bd["decoupe"]["temps_minutes"]), "Coût HT": fmt_eur(bd["decoupe"]["cout_total"])},
        {"Poste": "Pliage",           "Détail": f"{bd['pliage']['quantite']} pli(s) — {bd['pliage']['taux_horaire']} €/h",                   "Temps (min)": str(bd["pliage"]["temps_minutes"]),  "Coût HT": fmt_eur(bd["pliage"]["cout_total"])},
        {"Poste": "Perçage",          "Détail": f"{bd['percage']['quantite']} trou(s) — {bd['percage']['taux_horaire']} €/h",                "Temps (min)": str(bd["percage"]["temps_minutes"]), "Coût HT": fmt_eur(bd["percage"]["cout_total"])},
        {"Poste": "Montage/Finition", "Détail": f"{bd['montage']['quantite']} composant(s) — {bd['montage']['taux_horaire']} €/h",           "Temps (min)": str(bd["montage"]["temps_minutes"]), "Coût HT": fmt_eur(bd["montage"]["cout_total"])},
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    col_st, col_marge, col_ht, col_ttc = st.columns(4)
    col_st.metric("Sous-total HT", fmt_eur(bd["sous_total_ht"]))
    col_marge.metric(f"Marge ({bd['marge_pct']}%)", fmt_eur(bd["montant_marge"]))
    col_ht.metric("Total unitaire HT", fmt_eur(q["cout_unitaire_ht"]))
    col_ttc.metric(f"Total × {q['quantite']} TTC", fmt_eur(q["total_ttc"]))

    for w in q.get("warnings", []):
        st.warning(w)

# ── Tab Export ─────────────────────────────────────────────────────────────────
with tab_export:
    if "quotation" not in st.session_state:
        st.info("Générez d'abord un devis pour l'exporter.")
        st.stop()

    q = st.session_state["quotation"]
    bd = q["breakdown"]
    drawing = q["drawing_data"]

    st.subheader("Exporter le devis")

    col_json, col_excel = st.columns(2)

    with col_json:
        st.markdown("#### JSON structuré")
        json_str = json.dumps(q, indent=2, ensure_ascii=False, default=str)
        st.download_button("Télécharger le JSON", data=json_str.encode("utf-8"),
                           file_name=f"devis_{q['id_devis']}.json", mime="application/json",
                           use_container_width=True)

    with col_excel:
        st.markdown("#### Excel")
        excel_data = {
            "Référence pièce": [drawing.get("reference") or "—"],
            "Désignation":     [drawing.get("nom_piece") or "—"],
            "Client":          [q.get("client") or "—"],
            "Date":            [q["date_generation"][:10]],
            "N° Devis":        [q["id_devis"]],
            "Quantité":        [q["quantite"]],
            "Matière":         [drawing.get("matiere") or "—"],
            "Épaisseur (mm)":  [drawing.get("epaisseur_mm") or "—"],
            "Masse (g)":       [drawing.get("masse_estimee_g") or "—"],
            "Coût matière (€)":  [bd["matiere"]["cout_total"]],
            "Coût découpe (€)":  [bd["decoupe"]["cout_total"]],
            "Coût pliage (€)":   [bd["pliage"]["cout_total"]],
            "Coût perçage (€)":  [bd["percage"]["cout_total"]],
            "Coût montage (€)":  [bd["montage"]["cout_total"]],
            "Sous-total HT (€)": [bd["sous_total_ht"]],
            "Marge (%)":         [bd["marge_pct"]],
            "Total HT (€)":      [q["cout_unitaire_ht"]],
            "Total TTC (€)":     [q["total_ttc"]],
        }
        df_excel = pd.DataFrame(excel_data).T.reset_index()
        df_excel.columns = ["Champ", "Valeur"]
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="Devis")
        buf.seek(0)
        st.download_button("Télécharger l'Excel", data=buf.getvalue(),
                           file_name=f"devis_{q['id_devis']}.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
