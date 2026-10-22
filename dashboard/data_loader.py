"""
Data Loader - semua pemanggilan pickle/CSV dan caching Streamlit
dikumpulkan di sini, terpisah dari logika tampilan.
"""
import os
import pickle

import pandas as pd
import streamlit as st

from config import (
    MODEL_PATH, FEATURES_CSV, TRAIN_UNSCALED, TEST_UNSCALED, TEST_SCALED,
    ORDERS_DETAIL, RAW_EXCEL, RAW_MAIN_COLS, STOCK_EXCEL, RISK_SCORES_CSV, CRM_CUSTOMER_CSV,
)
from item_classifier import classify_series


def _stamp(*paths):
    """Waktu modifikasi file. Dipakai sebagai kunci cache supaya data/model
    otomatis dimuat ulang begitu file-nya berubah (mis. setelah retrain)."""
    return tuple(os.path.getmtime(p) if os.path.exists(p) else 0 for p in paths)



@st.cache_resource
def _load_model(stamp):
    if not os.path.exists(MODEL_PATH):
        st.error(f"File model tidak ditemukan di: {MODEL_PATH}")
        st.stop()
    with open(MODEL_PATH, "rb") as f:
        model_data = pickle.load(f)
    return model_data


@st.cache_data
def _load_data(stamp):
    if not os.path.exists(FEATURES_CSV):
        st.error(f"File data tidak ditemukan: {FEATURES_CSV}")
        st.stop()

    df_feat = pd.read_csv(FEATURES_CSV, parse_dates=["first_order_date", "last_order_date", "last_end_date"])
    train_u = pd.read_csv(TRAIN_UNSCALED) if os.path.exists(TRAIN_UNSCALED) else df_feat
    test_u  = pd.read_csv(TEST_UNSCALED) if os.path.exists(TEST_UNSCALED) else df_feat

    # Status ditentukan ATURAN End Date (bukan model): Churn = End Date terakhir < tanggal acuan.
    df_feat["churn_label"] = df_feat["churn_flag"].map({1: "Churn", 0: "Active"})

    # Skor risiko dari model (out-of-fold, dari modelling.ipynb Step 9b). Hanya bermakna
    # untuk pelanggan Aktif; pelanggan Churn statusnya pasti sehingga risikonya 100%.
    df_feat["risk_prob_model"] = float("nan")
    if os.path.exists(RISK_SCORES_CSV):
        risk = pd.read_csv(RISK_SCORES_CSV).drop_duplicates("Customer").set_index("Customer")["risk_prob"]
        df_feat["risk_prob_model"] = df_feat["Customer"].map(risk)

    # Opportunity & Notes dari CRM (hanya jenis pengadaan Rental). Kosong bila pelanggan belum punya opportunity.
    crm_cols = ["crm_company_name", "crm_n_opportunity", "crm_opportunity", "crm_notes", "crm_last_opportunity_date"]
    if os.path.exists(CRM_CUSTOMER_CSV):
        crm = pd.read_csv(CRM_CUSTOMER_CSV, parse_dates=["crm_last_opportunity_date"]).drop_duplicates("Customer")
        df_feat = df_feat.merge(crm, on="Customer", how="left")
        df_feat["crm_n_opportunity"] = df_feat["crm_n_opportunity"].fillna(0).astype(int)
    else:
        for c in crm_cols:
            df_feat[c] = 0 if c == "crm_n_opportunity" else None
    return df_feat, train_u, test_u


@st.cache_data
def _load_test_scaled(test_raw: pd.DataFrame, stamp):
    if os.path.exists(TEST_SCALED):
        return pd.read_csv(TEST_SCALED)
    return test_raw


@st.cache_data
def _load_item_category_breakdown(df_feat: pd.DataFrame, stamp):
    """
    Breakdown barang rental level-ITEM (satu baris = satu unit barang yang
    disewa), diklasifikasikan langsung dari nama barang aktual.

    Sumbernya sengaja dari file Excel mentah (bukan orders_churn_detailed.csv)
    karena file detail-order hanya menyimpan 1 baris per order dan kehilangan
    ~50% info barang (barang tercatat di baris child terpisah di Excel asli).
    Dengan forward-fill kolom order utama ke baris child (item), setiap unit
    barang bisa dikaitkan ke order & pelanggannya, sehingga SELURUH barang
    bisa ditampilkan apa adanya tanpa ditumpuk ke 'Lainnya'.
    """
    if not os.path.exists(RAW_EXCEL):
        return None

    raw = pd.read_excel(RAW_EXCEL)
    main_cols = [c for c in RAW_MAIN_COLS if c in raw.columns]
    raw[main_cols] = raw[main_cols].ffill()

    items = raw.dropna(subset=["Asset Rental Line /Product/Name"]).copy()
    items["item_category"] = classify_series(items["Asset Rental Line /Product/Name"])

    # Lampirkan churn_flag pelanggan (untuk churn-rate per kategori barang)
    if "Customer" in items.columns and "churn_flag" in df_feat.columns:
        churn_map = df_feat.set_index("Customer")["churn_flag"]
        items["churn_flag"] = items["Customer"].map(churn_map)

    return items


@st.cache_data
def _load_stock_category_breakdown(stamp):
    """
    Breakdown STOK barang aktual (bukan data order/transaksi), dari file
    master produk (mis. export Odoo "Product Template"). Satu baris = satu
    varian produk, dengan kolom "Quantity On Hand" (stok fisik saat ini) dan
    "Forecasted Quantity" (proyeksi setelah memperhitungkan order berjalan).

    Kategori barang (Mobil/Motor/Komputer-Laptop/dll) diklasifikasikan dari
    kolom "Name" pakai classifier yang sama dengan barang rental, supaya
    konsisten dengan tab "Barang Rental (Detail)".

    PENTING: data ini TIDAK berisi info pelanggan/order, jadi tidak bisa
    dikaitkan ke churn_flag - hanya untuk menampilkan jumlah stok per
    kategori, terpisah dari analisis churn per barang.
    """
    if not os.path.exists(STOCK_EXCEL):
        return None

    stock = pd.read_excel(STOCK_EXCEL)
    if "Name" not in stock.columns:
        return None

    stock = stock.dropna(subset=["Name"]).copy()
    stock["item_category"] = classify_series(stock["Name"])

    qty_col = "Quantity On Hand" if "Quantity On Hand" in stock.columns else None
    fcst_col = "Forecasted Quantity" if "Forecasted Quantity" in stock.columns else None
    if qty_col is None:
        return None

    agg_map = {qty_col: "sum"}
    if fcst_col:
        agg_map[fcst_col] = "sum"
    agg_map["Name"] = "count"

    summary = stock.groupby("item_category").agg(agg_map).reset_index()
    rename_map = {qty_col: "Jumlah Stok (On Hand)", "Name": "Jumlah Varian Produk"}
    if fcst_col:
        rename_map[fcst_col] = "Jumlah Stok (Forecast)"
    summary = summary.rename(columns=rename_map)
    summary = summary.rename(columns={"item_category": "Kategori Barang"})

    return summary


# ── Wrapper publik: nama & cara panggil tetap sama seperti sebelumnya ──────
def load_model():
    return _load_model(_stamp(MODEL_PATH))


def load_data():
    return _load_data(_stamp(FEATURES_CSV, TRAIN_UNSCALED, TEST_UNSCALED, RISK_SCORES_CSV, CRM_CUSTOMER_CSV))


def load_test_scaled(test_raw: pd.DataFrame):
    return _load_test_scaled(test_raw, _stamp(TEST_SCALED))


def load_item_category_breakdown(df_feat: pd.DataFrame):
    return _load_item_category_breakdown(df_feat, _stamp(RAW_EXCEL))


def load_stock_category_breakdown():
    return _load_stock_category_breakdown(_stamp(STOCK_EXCEL))
