"""
Churn Prediction Rental - Streamlit Dashboard
--------------------------------------------------------
Entry point tipis: load model/data lalu route ke modul halaman di pages/.
Semua path, tema, dan mapping kategori ada di config.py.
Semua fungsi loader ada di data_loader.py.
Semua helper kecil (format, gauge, sanitize) ada di utils.py.
"""
import warnings
# Force streamlit hot reload


import streamlit as st

from components import load_css, render_sidebar_header, render_sidebar_nav, render_footer
from config import BASE_DIR, PAGE_CONFIG
from data_loader import (
    load_model, load_data, load_item_category_breakdown, load_stock_category_breakdown,
)
from app_pages import overview, analisis_churn, prediksi_pelanggan, data_explorer
from utils import ensure_risk_scores

warnings.filterwarnings("ignore")

st.set_page_config(**PAGE_CONFIG)
load_css(f"{BASE_DIR}/style.css")

# ──────────────────────────────────────────────
#  LOAD MODEL & DATA
# ──────────────────────────────────────────────
try:
    model_bundle = load_model()
    model        = model_bundle["model"]
    feature_cols = model_bundle.get("feature_columns", model_bundle.get("feature_names", []))
except Exception as e:
    st.error(f"Gagal memuat model bundle: {e}")
    st.stop()

df_feat, train_raw, test_raw = load_data()
df_feat = ensure_risk_scores(df_feat, model, feature_cols)   # tambah kolom risk_prob
item_df = load_item_category_breakdown(df_feat)
stock_df = load_stock_category_breakdown()

# ──────────────────────────────────────────────
#  SIDEBAR & NAVIGATION
# ──────────────────────────────────────────────
with st.sidebar:
    render_sidebar_header()
    st.markdown("---")
    page = render_sidebar_nav()

# ──────────────────────────────────────────────
#  ROUTE
# ──────────────────────────────────────────────
if page == "🏠 Overview":
    overview.render(df_feat, model, feature_cols)
elif page == "📊 Analisis Churn":
    analisis_churn.render(df_feat, item_df, stock_df)
elif page == "🔍 Prediksi Pelanggan":
    prediksi_pelanggan.render(df_feat, model, feature_cols, test_raw)
elif page == "📋 Data Explorer":
    data_explorer.render(df_feat)

render_footer()
