"""
Config & Constants - Churn Prediction Rental Dashboard
--------------------------------------------------------
Satu-satunya tempat untuk path file, tema warna Plotly, dan mapping
kategori yang dipakai berulang di berbagai halaman. Kalau ada perubahan
nama kolom / kategori / warna, cukup ubah di sini saja (tidak perlu
menyisir setiap file page).
"""
import os

# ──────────────────────────────────────────────
#  PATH SETUP
# ──────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR    = os.path.dirname(BASE_DIR)
PROC_DIR    = os.path.join(ROOT_DIR, "data_preprocessing", "data", "processed")
RAW_DIR     = os.path.join(ROOT_DIR, "data_preprocessing", "data", "raw")
MODEL_PATH  = os.path.join(ROOT_DIR, "modelling", "models", "best_churn_model.pkl")
SCALER_PATH = os.path.join(PROC_DIR, "scaler.pkl")
LOGO_PATH   = os.path.join(BASE_DIR, "assets", "logo-poj-cropped.png")

DATA_UPDATED_LABEL = "7 Oktober 2026"

FEATURES_CSV   = os.path.join(PROC_DIR, "customer_churn_features.csv")
TRAIN_UNSCALED = os.path.join(PROC_DIR, "train_unscaled.csv")
TEST_UNSCALED  = os.path.join(PROC_DIR, "test_unscaled.csv")
TEST_SCALED    = os.path.join(PROC_DIR, "test_scaled.csv")
ORDERS_DETAIL  = os.path.join(PROC_DIR, "orders_churn_detailed.csv")
RISK_SCORES_CSV = os.path.join(PROC_DIR, "customer_risk_scores.csv")   # skor risiko out-of-fold per pelanggan
CRM_CUSTOMER_CSV = os.path.join(PROC_DIR, "customer_crm_info.csv")      # opportunity & notes CRM per pelanggan (Preprocessing Step 23)
RAW_EXCEL      = os.path.join(RAW_DIR, "Data-Mentah-Rental-Order.xlsx")
STOCK_EXCEL    = os.path.join(RAW_DIR, "Data-Stok-Barang.xlsx")

# Kolom "main row" yang perlu di-forward-fill supaya baris item (child row)
# ikut punya info order/customer-nya (sama seperti langkah di Preprocessing.ipynb)
RAW_MAIN_COLS = [
    "Order Reference", "Order Date", "Customer", "Rental Quotation", "Start Date",
    "End Date", "Status", "SMS Rental State", "Total Invoiced", "Total Paid", "Project Value",
]

# ──────────────────────────────────────────────
#  PAGE CONFIG
# ──────────────────────────────────────────────
PAGE_CONFIG = dict(
    page_title="Dashboard Churn Pelanggan Rental | Pesonna Optima Jasa",
    page_icon=LOGO_PATH,
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navigasi sidebar dalam bentuk list, dikelompokkan per kategori.
# Dipakai oleh components.render_sidebar_nav().
NAV_GROUPS = {
    "Ringkasan": [
        "🏠 Overview",
    ],
    "Analisis Data": [
        "📊 Analisis Churn",
        "📋 Data Explorer",
    ],
    "Prediksi": [
        "🔍 Prediksi Pelanggan",
    ],
}
NAV_PAGES = [p for pages in NAV_GROUPS.values() for p in pages]

# ──────────────────────────────────────────────
#  PLOTLY LIGHT THEME & COLOR CONSTANTS
#  (disamakan dengan warna brand PT Pesonna Optima Jasa: hijau tua & hijau muda)
# ──────────────────────────────────────────────
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#ffffff",
    font=dict(family="Inter", color="#1e293b"),
    title_font=dict(family="Inter", color="#154a24", size=15),
    xaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1"),
    yaxis=dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1"),
    legend=dict(bgcolor="#ffffff", bordercolor="#cbd5e1", borderwidth=1),
    margin=dict(l=20, r=20, t=45, b=20),
)
COLOR_CHURN   = "#ef4444"
COLOR_ACTIVE  = "#29823e"   # hijau tua brand POJ
COLOR_BLUE    = "#29823e"
COLOR_ACCENT  = "#6abb3a"   # hijau muda brand POJ
RISK_SCALE    = ["#6abb3a", "#f6ad55", "#fc8181"]

# ──────────────────────────────────────────────
#  MODEL FEATURE CATEGORY MAPPINGS
#  (dipakai di halaman Analisis Churn & Prediksi Pelanggan,
#   sebelumnya diduplikasi di dua tempat berbeda)
# ──────────────────────────────────────────────

# Kategori dominan pelanggan (fitur one-hot yang dipakai model)
DOMINANT_CATEGORY_COLS = {
    "dominant_product_category_Komputer_Laptop": "Komputer/Laptop",
    "dominant_product_category_Lainnya": "Lainnya",
    "dominant_product_category_Mobil": "Mobil",
    "dominant_product_category_Motor": "Motor",
    "dominant_product_category_Televisi": "Televisi",
}

# Persentase kategori per pelanggan (fitur numerik yang dipakai model)
PCT_CATEGORY_COLS = {
    "Komputer/Laptop": "pct_komputer_laptop",
    "Lainnya": "pct_lainnya",
    "Mobil": "pct_mobil",
    "Motor": "pct_motor",
    "Televisi": "pct_televisi",
}

# Opsi kategori dominan yang bisa dipilih user di form Input Manual
DOMINANT_CATEGORY_OPTIONS = ["Mobil", "Motor", "Komputer/Laptop", "Televisi", "Lainnya"]

# Kategori frekuensi order (fitur one-hot yang dipakai model)
FREQ_CATEGORY_COLS = {
    "one_time": "order_frequency_category_one_time",
    "rare": "order_frequency_category_rare",
    "occasional": "order_frequency_category_occasional",
    "regular": "order_frequency_category_regular",
    "frequent": "order_frequency_category_frequent",
}
FREQ_CATEGORY_OPTIONS = list(FREQ_CATEGORY_COLS.keys())

# Label tampilan untuk kategori frekuensi (dipakai di tab Analisis Churn)
FREQ_DISPLAY_LABELS = {
    "order_frequency_category_frequent": "Frequent",
    "order_frequency_category_occasional": "Occasional",
    "order_frequency_category_one_time": "One-Time",
    "order_frequency_category_rare": "Rare",
    "order_frequency_category_regular": "Regular",
}

MONTH_LABELS = {1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "Mei", 6: "Jun",
                7: "Jul", 8: "Agu", 9: "Sep", 10: "Okt", 11: "Nov", 12: "Des"}


# ── Skor risiko gabungan (model + sinyal perilaku) ────────────────────────
# Skor model sangat dipengaruhi status SMS/order (kontrak masih berjalan), sehingga
# pelanggan Aktif dengan jeda order panjang bisa tetap berskor ~0%. Sinyal perilaku
# (jeda order, frekuensi, sisa kontrak, pembayaran, status SMS On Going) ditambahkan
# supaya skor konsisten dengan alasan yang ditampilkan.
#   skor_final = skor_model + (1 - skor_model) * BEHAVIOR_WEIGHT * skor_perilaku
BEHAVIOR_WEIGHT = 0.6
