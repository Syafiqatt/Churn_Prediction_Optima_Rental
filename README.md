# Churn Prediction Rental

Project machine learning untuk memprediksi churn pelanggan rental (mobil, motor,
komputer/laptop, dan barang lainnya), lengkap dengan dashboard interaktif untuk
tim bisnis.

## Struktur Folder

```
Churn Prediction Rental/
├── data_preprocessing/       # Raw data -> fitur siap-model
│   ├── data/
│   │   ├── raw/               # Data-Mentah-Rental-Order.xlsx (sumber asli)
│   │   └── processed/         # Output: customer_churn_features.csv, train/test, dll
│   ├── src/Preprocessing.ipynb
│   ├── EDA.ipynb
│   └── README.md              # Detail 22 step pipeline preprocessing
│
├── modelling/                 # Training, seleksi model, & validasi performa
│   ├── modelling.ipynb         # Step 1-9 training + Step 10 validasi backtest temporal
│   └── models/best_churn_model.pkl   # Model final (XGBoost) + metadata
│
└── dashboard/                 # Aplikasi Streamlit untuk eksplorasi & prediksi
    ├── app.py                 # Entry point (router tipis)
    ├── config.py               # Semua path/tema/mapping kategori terpusat
    ├── utils.py                 # Fungsi bantu (format, gauge chart, sanitize)
    ├── data_loader.py           # Load model & data (cached)
    ├── item_classifier.py       # Klasifikasi kategori barang rental
    ├── components.py            # Komponen tampilan (HTML/CSS reusable)
    ├── app_pages/                # 1 file = 1 halaman dashboard
    │   ├── overview.py
    │   ├── analisis_churn.py
    │   ├── evaluasi_model.py
    │   ├── prediksi_pelanggan.py
    │   └── data_explorer.py
    ├── style.css
    ├── requirements.txt
    └── README.md
```

## Alur Kerja

1. **`data_preprocessing/`** — ubah Excel transaksi mentah menjadi fitur
   level-pelanggan yang siap dipakai model (lihat `data_preprocessing/README.md`).
2. **`modelling/`** — training beberapa algoritma & pilih model terbaik
   (LightGBM, ROC-AUC ≈ 0.98 di test set — lihat bagian "Definisi Churn" di
   bawah soal kenapa angka ini tidak sama dengan kemampuan memprediksi masa
   depan), disimpan sebagai `modelling/models/best_churn_model.pkl`. Juga
   menghasilkan `customer_risk_scores.csv` (skor risiko out-of-fold per
   pelanggan) yang dipakai dashboard.
3. **`dashboard/`** — aplikasi Streamlit yang membaca hasil step 1 & 2 untuk
   menampilkan analitik dan melakukan prediksi churn (lihat `dashboard/README.md`).

## Menjalankan Dashboard

```bash
cd "Churn Prediction Rental/dashboard"
pip install -r requirements.txt
streamlit run app.py
```

## Definisi Churn (Revisi)

Status pelanggan ditentukan oleh **tanggal berakhir kontrak (End Date)** pada
tanggal acuan `REFERENCE_DATE` (saat ini **29 September 2026**, diatur di
`Preprocessing.ipynb`):

| Kondisi | Status |
|---|---|
| End Date **terakhir** pelanggan **sebelum** tanggal acuan (semua kontrak sudah habis) | **Churn** (pasti, risiko 100%) |
| End Date terakhir pelanggan **pada/sesudah** tanggal acuan (masih ada kontrak berjalan) | **Aktif** (pasti) |

Yang dipakai adalah End Date *terbesar* per pelanggan, jadi pelanggan yang
kontrak lamanya habis tapi masih punya kontrak baru berjalan tetap Aktif.
Hasil saat ini: 195 Churn (31,9%) dan 416 Aktif (68,1%) dari 611 pelanggan.

**Persentase risiko churn hanya untuk pelanggan Aktif** dan dihitung model dari
sinyal lain (status SMS Rental, status order, pembayaran, pola order, dll).
Persentase ini memberi prioritas follow-up perpanjangan, bukan penentu status.

Catatan membaca performa model:
- ROC-AUC test set (~0.98) mengukur seberapa mirip profil pelanggan dengan
  pelanggan yang kontraknya *sudah* habis (label = End Date). Ini bukan
  kemampuan memprediksi masa depan.
- Fitur yang bisa merekonstruksi End Date (recency, umur/rentang order pelanggan,
  overdue, tahun akuisisi) sengaja dikeluarkan dari fitur model.
- Estimasi jujur untuk "kontrak akan habis, apakah diperpanjang?" ada di
  `modelling.ipynb` Step 10 (backtest temporal): ROC-AUC ≈ 0.69–0.71.
- Skor risiko pelanggan Aktif memakai nilai out-of-fold supaya tidak terlalu
  optimis. Pelanggan Aktif yang status SMS-nya masih "Unknown" cenderung
  mendapat skor tinggi karena status itu sebagian besar muncul di order lama
  yang sudah selesai — cek kelengkapan data statusnya sebelum menindaklanjuti.

## Catatan Penting: Kategori Barang Rental

Fitur `dominant_product_category` yang dipakai **model prediksi** diturunkan dari
nama pelanggan (mis. "PT X - Rental Komputer") saat preprocessing — cara ini
menyisakan ~20% order di kategori generik "Lainnya" karena banyak nama pelanggan
tidak menyebutkan jenis barangnya secara eksplisit. Fitur ini **tidak diubah**
supaya model yang sudah dilatih tetap valid.

Untuk kebutuhan **analisis/visualisasi**, dashboard punya klasifikasi kategori
barang yang jauh lebih akurat (`dashboard/item_classifier.py`), diturunkan
langsung dari nama unit barang yang disewa (level-item, dari Excel mentah).
Cakupannya ~99.98% — hampir semua barang tampil dengan kategori aslinya
(Mobil, Motor, Komputer/Laptop, Handphone, Tablet, Printer, Scanner, dll),
bukan ditumpuk ke satu label "Lainnya". Lihat tab **"🧾 Barang Rental (Detail)"**
di halaman Analisis Churn pada dashboard.

## Opportunity & Notes dari CRM

Data `data_preprocessing/data/raw/crm.lead.xlsx` diproses di `Preprocessing.ipynb` Step 23 dengan aturan:
hanya `Jenis Pengadaan` = Rental; `Company Name` `-`/kosong diganti `Customer/Name` (keduanya kosong = dihapus);
`SYNAPS` diganti `PT. MITRA SETIA SEHAT - Rental`. Hasilnya (`customer_crm_info.csv`) ditampilkan di dashboard:
halaman Prediksi Pelanggan (daftar Opportunity + Notes), watchlist Overview, dan tabel Data Explorer.
Tidak memengaruhi fitur maupun model churn. Pelanggan yang namanya tidak cocok dengan data CRM tampil kosong.
