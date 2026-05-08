"""
Interface Streamlit — MAJI Analyse de Plans Techniques & Génération de Devis

Parcours utilisateur :
  1. Upload du plan (PDF ou image)
  2. Analyse automatique (prétraitement → OCR → Vision IA)
  3. Visualisation des données extraites
  4. Paramétrage du devis (quantité, marge, client)
  5. Génération et export du devis
"""

import io
import json
import os
import sys
from pathlib import Path

import pandas as pd
import requests
import streamlit as st
from PIL import Image

# ── Configuration ─────────────────────────────────────────────────────────────
API_BASE = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")

st.set_page_config(
    page_title="MAJI — Analyse Plans & Devis",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles CSS ─────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem; border-radius: 12px; margin-bottom: 2rem;
        color: white; text-align: center;
    }
    .metric-card {
        background: #f8f9fa; border-left: 4px solid #0f3460;
        padding: 1rem; border-radius: 8px; margin: 0.5rem 0;
    }
    .warning-box {
        background: #fff3cd; border-left: 4px solid #ffc107;
        padding: 1rem; border-radius: 8px;
    }
    .success-box {
        background: #d4edda; border-left: 4px solid #28a745;
        padding: 1rem; border-radius: 8px;
    }
    .cost-table th { background: #0f3460; color: white; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>🏭 MAJI — Analyse de Plans Techniques</h1>
        <p>Extraction intelligente · Génération automatique de devis · Tôlerie & Usinage</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Fonctions utilitaires ──────────────────────────────────────────────────────

def call_analyze(file_bytes: bytes, filename: str) -> dict:
    resp = requests.post(
        f"{API_BASE}/drawings/analyze",
        files={"file": (filename, file_bytes, _content_type(filename))},
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()


def call_generate_quotation(payload: dict) -> dict:
    resp = requests.post(
        f"{API_BASE}/quotations/generate",
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _content_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return {
        ".pdf": "application/pdf",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".tiff": "image/tiff",
        ".bmp": "image/bmp",
    }.get(ext, "application/octet-stream")


def fmt_eur(value: float) -> str:
    return f"{value:,.4f} €".replace(",", " ")


# ── Sidebar — Paramètres ───────────────────────────────────────────────────────
with st.sidebar:
    st.header("⚙️ Paramètres")
    st.divider()

    st.subheader("Devis")
    quantite = st.number_input("Quantité", min_value=1, value=1, step=1)
    marge_pct = st.slider("Marge commerciale (%)", 0, 80, 30, step=5) / 100
    client = st.text_input("Client", placeholder="Ex: Airbus Group")

    st.divider()
    st.subheader("Tarifs (€/h)")
    taux_machine = st.number_input("Taux machine (laser/presse)", value=85.0, step=5.0)
    taux_operateur = st.number_input("Taux opérateur", value=35.0, step=5.0)

    st.divider()
    st.subheader("API")
    api_url = st.text_input("URL de l'API", value=API_BASE)
    if api_url != API_BASE:
        API_BASE = api_url

    # Test de connexion
    try:
        r = requests.get(f"{api_url.replace('/api/v1', '')}/health", timeout=3)
        if r.status_code == 200:
            st.success("✅ API connectée")
        else:
            st.warning("⚠️ API non disponible")
    except Exception:
        st.error("❌ API inaccessible")

# ── Zone principale ────────────────────────────────────────────────────────────
tab_upload, tab_results, tab_quotation, tab_export = st.tabs(
    ["📤 Upload", "🔍 Analyse", "💶 Devis", "📥 Export"]
)

# ─────────────────────────────────────────────────────────
# TAB 1 — Upload & lancement de l'analyse
# ─────────────────────────────────────────────────────────
with tab_upload:
    st.subheader("Importer un plan technique")

    col_drop, col_info = st.columns([2, 1])

    with col_drop:
        uploaded_file = st.file_uploader(
            "Déposez votre plan ici",
            type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"],
            help="Plans techniques de pièces de tôlerie ou d'usinage",
        )

        if uploaded_file:
            st.session_state["uploaded_filename"] = uploaded_file.name
            st.session_state["uploaded_bytes"] = uploaded_file.read()

            # Prévisualisation
            if uploaded_file.name.lower().endswith(".pdf"):
                st.info(f"📄 PDF chargé : **{uploaded_file.name}**")
            else:
                try:
                    img = Image.open(io.BytesIO(st.session_state["uploaded_bytes"]))
                    st.image(img, caption=uploaded_file.name, use_container_width=True)
                except Exception:
                    st.warning("Prévisualisation impossible")

    with col_info:
        st.markdown(
            """
            **Formats acceptés**
            - PDF (plans multi-pages : 1ère page analysée)
            - PNG, JPEG, TIFF, BMP

            **Ce que l'IA extrait**
            - Dimensions (L × l × h)
            - Percages (Ø, quantité, tolérance)
            - Pliages (angle, rayon, longueur)
            - Nomenclature (REP/DESIGNATION/QTÉ)
            - Tolérances & notes techniques
            - Matière, épaisseur, masse

            **Technologies**
            - OpenCV (prétraitement)
            - PaddleOCR (extraction texte)
            - GPT-4o Vision (compréhension)
            """
        )

    st.divider()

    if st.session_state.get("uploaded_bytes"):
        btn_col, info_col = st.columns([1, 3])
        with btn_col:
            analyze_btn = st.button(
                "🚀 Lancer l'analyse", type="primary", use_container_width=True
            )
        with info_col:
            st.caption(
                "L'analyse prend 10–30 secondes selon la complexité du plan "
                "(prétraitement + OCR + Vision IA GPT-4o)."
            )

        if analyze_btn:
            with st.spinner("Analyse en cours… Prétraitement → OCR → Vision IA…"):
                try:
                    result = call_analyze(
                        st.session_state["uploaded_bytes"],
                        st.session_state["uploaded_filename"],
                    )
                    st.session_state["extraction_result"] = result
                    st.success(
                        f"✅ Analyse terminée en {result.get('processing_time_ms', 0)} ms — "
                        f"{len(result.get('ocr_raw', []))} éléments OCR détectés"
                    )

                    if result.get("warnings"):
                        for w in result["warnings"]:
                            st.warning(f"⚠️ {w}")

                    st.info("👉 Consultez l'onglet **Analyse** pour les résultats détaillés")

                except requests.HTTPError as e:
                    st.error(f"Erreur API ({e.response.status_code}): {e.response.text}")
                except Exception as e:
                    st.error(f"Erreur: {e}")

# ─────────────────────────────────────────────────────────
# TAB 2 — Résultats d'extraction
# ─────────────────────────────────────────────────────────
with tab_results:
    if "extraction_result" not in st.session_state:
        st.info("⬅️ Uploadez un plan et lancez l'analyse pour voir les résultats ici.")
        st.stop()

    result = st.session_state["extraction_result"]
    drawing = result.get("drawing_data", {})
    dims = drawing.get("dimensions", {})
    ocr_items = result.get("ocr_raw", [])

    st.subheader("🔍 Données extraites du plan")

    # Métriques clés
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Confiance IA", f"{drawing.get('confidence_score', 0):.0%}")
    col2.metric("Éléments OCR", len(ocr_items))
    col3.metric("Percages", len(drawing.get("percages", [])))
    col4.metric("Pliages", len(drawing.get("pliages", [])))

    st.divider()

    # Informations générales
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("#### 🔩 Identification de la pièce")
        info_data = {
            "Nom / Désignation": drawing.get("nom_piece") or "—",
            "Référence": drawing.get("reference") or "—",
            "Matière": drawing.get("matiere") or "—",
            "Nuance": drawing.get("nuance") or "—",
            "Épaisseur (mm)": drawing.get("epaisseur_mm") or "—",
            "Masse estimée (g)": drawing.get("masse_estimee_g") or "—",
            "Traitement surface": drawing.get("traitement_surface") or "—",
        }
        for k, v in info_data.items():
            st.markdown(f"**{k}** : {v}")

    with col_right:
        st.markdown("#### 📐 Dimensions")
        dim_data = {
            "Longueur (mm)": dims.get("longueur_mm") or "—",
            "Largeur (mm)": dims.get("largeur_mm") or "—",
            "Hauteur (mm)": dims.get("hauteur_mm") or "—",
            "Surface dépliée (mm²)": dims.get("surface_depliee_mm2") or "—",
            "Périmètre découpe (mm)": dims.get("perimetre_decoupe_mm") or "—",
        }
        for k, v in dim_data.items():
            st.markdown(f"**{k}** : {v}")

    st.divider()

    # Percages
    percages = drawing.get("percages", [])
    if percages:
        st.markdown("#### ⭕ Percages")
        df_perc = pd.DataFrame(percages)
        st.dataframe(df_perc, use_container_width=True, hide_index=True)
    else:
        st.markdown("#### ⭕ Percages — _aucun détecté_")

    # Pliages
    pliages = drawing.get("pliages", [])
    if pliages:
        st.markdown("#### 📏 Pliages")
        df_pli = pd.DataFrame(pliages)
        st.dataframe(df_pli, use_container_width=True, hide_index=True)

    # Nomenclature
    nomenclature = drawing.get("nomenclature", [])
    if nomenclature:
        st.markdown("#### 📋 Nomenclature (BOM)")
        df_nom = pd.DataFrame(nomenclature)
        st.dataframe(df_nom, use_container_width=True, hide_index=True)

    # Tolérances & notes
    col_tol, col_notes = st.columns(2)
    with col_tol:
        tol = drawing.get("tolerances", {})
        st.markdown("#### 🎯 Tolérances")
        st.markdown(f"**Générales** : {tol.get('generales') or '—'}")
        for spec in tol.get("specifiques", []):
            st.markdown(f"- {spec}")

    with col_notes:
        notes = drawing.get("notes_techniques", [])
        st.markdown("#### 📝 Notes techniques")
        for note in notes:
            st.markdown(f"- {note}")

    st.divider()

    # OCR brut (optionnel)
    with st.expander(f"🔤 Textes OCR bruts ({len(ocr_items)} éléments)"):
        if ocr_items:
            df_ocr = pd.DataFrame(ocr_items)[["text", "confidence", "is_rotated"]]
            df_ocr["confidence"] = df_ocr["confidence"].map(lambda x: f"{x:.1%}")
            st.dataframe(df_ocr, use_container_width=True, hide_index=True)
        else:
            st.info("Aucun résultat OCR disponible")

    with st.expander("📄 JSON brut complet"):
        st.json(result)

# ─────────────────────────────────────────────────────────
# TAB 3 — Génération de devis
# ─────────────────────────────────────────────────────────
with tab_quotation:
    if "extraction_result" not in st.session_state:
        st.info("⬅️ Analysez d'abord un plan pour générer un devis.")
        st.stop()

    drawing_data = st.session_state["extraction_result"]["drawing_data"]

    st.subheader("💶 Génération du devis")
    st.caption(
        "Les coûts sont calculés à partir des données extraites du plan. "
        "Vérifiez les paramètres dans la barre latérale avant de générer."
    )

    gen_btn = st.button("📊 Calculer le devis", type="primary")

    if gen_btn:
        payload = {
            "drawing_data": drawing_data,
            "quantite": quantite,
            "marge_pct": marge_pct,
            "taux_horaire_machine": taux_machine,
            "taux_horaire_operateur": taux_operateur,
            "client": client or None,
        }

        with st.spinner("Calcul du devis en cours…"):
            try:
                quotation = call_generate_quotation(payload)
                st.session_state["quotation"] = quotation
            except Exception as e:
                st.error(f"Erreur: {e}")
                st.stop()

    if "quotation" not in st.session_state:
        st.stop()

    q = st.session_state["quotation"]
    bd = q["breakdown"]

    # En-tête du devis
    st.divider()
    col_id, col_date, col_ref = st.columns(3)
    col_id.metric("N° Devis", q["id_devis"])
    col_date.metric("Date", q["date_generation"][:10])
    col_ref.metric("Référence pièce", q.get("reference_piece") or "—")

    if q.get("client"):
        st.markdown(f"**Client** : {q['client']}")

    st.divider()

    # Tableau de décomposition des coûts
    st.markdown("#### 📊 Décomposition des coûts")

    cost_rows = [
        {
            "Poste": "🔩 Matière",
            "Détail": f"{bd['matiere']['masse_kg']} kg × {bd['matiere']['prix_unitaire_kg']} €/kg",
            "Temps (min)": "—",
            "Coût HT": fmt_eur(bd["matiere"]["cout_total"]),
        },
        {
            "Poste": "⚡ Découpe laser",
            "Détail": f"{bd['decoupe']['taux_horaire']} €/h",
            "Temps (min)": f"{bd['decoupe']['temps_minutes']}",
            "Coût HT": fmt_eur(bd["decoupe"]["cout_total"]),
        },
        {
            "Poste": "📐 Pliage",
            "Détail": f"{bd['pliage']['quantite']} pli(s) — {bd['pliage']['taux_horaire']} €/h",
            "Temps (min)": f"{bd['pliage']['temps_minutes']}",
            "Coût HT": fmt_eur(bd["pliage"]["cout_total"]),
        },
        {
            "Poste": "⭕ Perçage",
            "Détail": f"{bd['percage']['quantite']} trou(s) — {bd['percage']['taux_horaire']} €/h",
            "Temps (min)": f"{bd['percage']['temps_minutes']}",
            "Coût HT": fmt_eur(bd["percage"]["cout_total"]),
        },
        {
            "Poste": "🔧 Montage / Finition",
            "Détail": f"{bd['montage']['quantite']} composant(s) — {bd['montage']['taux_horaire']} €/h",
            "Temps (min)": f"{bd['montage']['temps_minutes']}",
            "Coût HT": fmt_eur(bd["montage"]["cout_total"]),
        },
    ]

    st.dataframe(pd.DataFrame(cost_rows), use_container_width=True, hide_index=True)

    # Totaux
    st.divider()
    col_st, col_marge, col_ht, col_ttc = st.columns(4)
    col_st.metric("Sous-total HT", fmt_eur(bd["sous_total_ht"]))
    col_marge.metric(f"Marge ({bd['marge_pct']}%)", fmt_eur(bd["montant_marge"]))
    col_ht.metric("Total unitaire HT", fmt_eur(q["cout_unitaire_ht"]))
    col_ttc.metric(
        f"Total × {q['quantite']} TTC",
        fmt_eur(q["total_ttc"]),
        delta=None,
    )

    # Warnings
    if q.get("warnings"):
        st.divider()
        for w in q["warnings"]:
            st.warning(f"⚠️ {w}")

# ─────────────────────────────────────────────────────────
# TAB 4 — Export
# ─────────────────────────────────────────────────────────
with tab_export:
    if "quotation" not in st.session_state:
        st.info("⬅️ Générez d'abord un devis pour pouvoir l'exporter.")
        st.stop()

    q = st.session_state["quotation"]
    st.subheader("📥 Exporter le devis")

    col_json, col_excel = st.columns(2)

    with col_json:
        st.markdown("#### JSON structuré")
        json_str = json.dumps(q, indent=2, ensure_ascii=False, default=str)
        st.download_button(
            "⬇️ Télécharger le JSON",
            data=json_str.encode("utf-8"),
            file_name=f"devis_{q['id_devis']}.json",
            mime="application/json",
            use_container_width=True,
        )
        with st.expander("Aperçu JSON"):
            st.json(q)

    with col_excel:
        st.markdown("#### Excel (fiche de devis)")
        bd = q["breakdown"]
        drawing = q["drawing_data"]

        excel_data = {
            "Référence pièce": [drawing.get("reference") or "—"],
            "Désignation": [drawing.get("nom_piece") or "—"],
            "Client": [q.get("client") or "—"],
            "Date": [q["date_generation"][:10]],
            "N° Devis": [q["id_devis"]],
            "Quantité": [q["quantite"]],
            "Matière": [drawing.get("matiere") or "—"],
            "Épaisseur (mm)": [drawing.get("epaisseur_mm") or "—"],
            "Masse (g)": [drawing.get("masse_estimee_g") or "—"],
            "Coût matière (€)": [bd["matiere"]["cout_total"]],
            "Coût découpe (€)": [bd["decoupe"]["cout_total"]],
            "Coût pliage (€)": [bd["pliage"]["cout_total"]],
            "Coût perçage (€)": [bd["percage"]["cout_total"]],
            "Coût montage (€)": [bd["montage"]["cout_total"]],
            "Sous-total HT (€)": [bd["sous_total_ht"]],
            "Marge (%)": [bd["marge_pct"]],
            "Total HT (€)": [q["cout_unitaire_ht"]],
            "Total TTC (€)": [q["total_ttc"]],
        }

        df_excel = pd.DataFrame(excel_data).T.reset_index()
        df_excel.columns = ["Champ", "Valeur"]

        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as writer:
            df_excel.to_excel(writer, index=False, sheet_name="Devis")
        buf.seek(0)

        st.download_button(
            "⬇️ Télécharger l'Excel",
            data=buf.getvalue(),
            file_name=f"devis_{q['id_devis']}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
