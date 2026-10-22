"""
Item Classifier - Kategori Barang Rental (Item-Level)
--------------------------------------------------------
Kategori "dominant_product_category" yang dipakai model (Mobil / Motor /
Komputer-Laptop / Televisi / Lainnya) diturunkan dari NAMA PELANGGAN
("PT ... - Rental Komputer"), bukan dari barang yang benar-benar disewa.
Akibatnya sekitar 20% order jatuh ke bucket "Lainnya" padahal barangnya
jelas (mobil, laptop, motor, dll) hanya karena nama pelanggan tidak
menyebutkan kategori secara eksplisit.

Modul ini mengklasifikasikan barang berdasarkan teks aktual di kolom
"Rental Serial Lines/Product" (nama unit yang disewa), sehingga hampir
semua barang bisa dikenali kategorinya dan "Lainnya" tersisa sangat kecil.

PENTING: kategori di sini HANYA untuk keperluan analisis & visualisasi
di dashboard. Fitur yang dipakai model prediksi (dominant_product_category,
pct_*) TIDAK diubah, supaya model yang sudah dilatih tetap valid.
"""
import re

MOTOR_KEYWORDS = [
    "vario", "beat", "crf", "cb150", "supra", "nmax", "klx", "scoopy", "pcx",
    "vespa", "ninja", "yamaha", "kawasaki", "electric motor", "maka", "alva",
    "gesits", "niu", "revo",
]

MOBIL_KEYWORDS = [
    "toyota", "honda civic", "honda hrv", "honda brio", "honda crv", "honda jazz",
    "honda mobilio", "mitsubishi", "daihatsu", "suzuki", "isuzu", "hyundai", "byd",
    "denza", "lexus", "nissan", "wuling", "kia", "chery", "tesla", "mercedes", "bmw",
    "fortuner", "innova", "avanza", "xpander", "rush", "calya", "veloz", "xenia",
    "terios", "luxio", "granmax", "xl7", "ertiga", "hilux", "hiace", "camry",
    "altis", "vios", "yaris", "palisade", "santa fe", "ioniq", "pajero", "triton",
    "l300", "elf", "traga",
]

PRINTER_KEYWORDS  = ["printer"]
SCANNER_KEYWORDS  = ["scanner"]
TABLET_KEYWORDS   = ["tab samsung", "galaxy tab", "ipad", " tab "]
PHONE_KEYWORDS    = ["handphone", "iphone", "galaxy s23", "galaxy s10", "galaxy s2"]
LAPTOP_KEYWORDS   = [
    "laptop", "lenovo", "asus", "dell", "macbook", "apple", "microsoft surface",
    "msi", "thinkpad", "thinkbook", "ideapad", "vivobook", "zenbook", "yoga",
    "optiplex", "latitude", "xps", "elitebook", "probook", "zbook", "notebook",
    "aio", "hp omnibook", "hp elite", "hp pro", "hp envy", "hp pavilion",
    "hp 240", "hp 280", "hp prodesk",
]
TV_KEYWORDS       = [" tv", "televisi", "smart tv"]
MONITOR_KEYWORDS  = ["monitor", "projector"]
OFFICE_KEYWORDS   = ["mesin hitung uang"]

UNKNOWN_LABEL = "Lainnya (Belum Teridentifikasi)"


def classify_item(text) -> str:
    """Klasifikasikan satu nama barang rental ke kategori item-level."""
    if text is None:
        return UNKNOWN_LABEL
    t = f" {str(text).strip().lower()} "
    if not t.strip():
        return UNKNOWN_LABEL

    if any(k in t for k in PRINTER_KEYWORDS):
        return "Printer"
    if any(k in t for k in SCANNER_KEYWORDS):
        return "Scanner"
    if any(k in t for k in PHONE_KEYWORDS):
        return "Handphone"
    if any(k in t for k in TABLET_KEYWORDS):
        return "Tablet"
    if any(k in t for k in MOTOR_KEYWORDS):
        return "Motor"
    if any(k in t for k in MOBIL_KEYWORDS):
        return "Mobil"
    if any(k in t for k in LAPTOP_KEYWORDS):
        return "Komputer/Laptop"
    if any(k in t for k in TV_KEYWORDS):
        return "Televisi"
    if any(k in t for k in MONITOR_KEYWORDS):
        return "Monitor/Proyektor"
    if any(k in t for k in OFFICE_KEYWORDS):
        return "Peralatan Kantor"
    return UNKNOWN_LABEL


def classify_series(series):
    """Terapkan classify_item ke seluruh pandas Series sekaligus."""
    return series.apply(classify_item)