# Dashboard — Churn Prediction Rental

Dashboard Streamlit untuk memantau & memprediksi churn pelanggan rental.

## Menjalankan

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dashboard butuh file-file berikut sudah tersedia (dihasilkan dari
`data_preprocessing/` dan `modelling/`, lihat README di root project):

- `../modelling/models/best_churn_model.pkl`
- `../data_preprocessing/data/processed/customer_churn_features.csv`
- `../data_preprocessing/data/processed/customer_risk_scores.csv`
  (skor risiko out-of-fold per pelanggan, dihasilkan `modelling.ipynb` Step 9b; kalau
  tidak ada, dashboard menghitung dari model langsung yang hasilnya lebih optimis)
- `../data_preprocessing/data/processed/train_unscaled.csv`
- `../data_preprocessing/data/processed/test_unscaled.csv`
- `../data_preprocessing/data/processed/test_scaled.csv`
- `../data_preprocessing/data/raw/Data-Mentah-Rental-Order.xlsx`
  (dipakai untuk breakdown barang rental level-item di tab
  "Barang Rental (Detail)")

> **Catatan versi:** `best_churn_model.pkl` dilatih dengan scikit-learn 1.8.0 dan lightgbm 4.7.0.
> File pickle terikat versi library; kalau dashboard gagal memuat model di environment Anda,
> jalankan ulang `modelling/modelling.ipynb` di environment tersebut untuk membuat ulang file model.

## Aturan Status & Risiko

- **Status** dari End Date terakhir pelanggan terhadap tanggal acuan (`REFERENCE_DATE` di
  `Preprocessing.ipynb`): sebelum tanggal acuan = **Churn** (risiko 100%), pada/sesudahnya = **Aktif**.
- **Persentase risiko** hanya bermakna untuk pelanggan Aktif (skor model dari SMS Rental,
  status order, pembayaran, dll). Level: >=70% Tinggi, 40-70% Sedang, <40% Rendah.
- Saat data di-refresh atau tanggal acuan berubah: jalankan ulang `Preprocessing.ipynb` lalu
  `modelling.ipynb`.

## Struktur Kode

| File / Folder | Isi |
|---|---|
| `app.py` | Entry point. Load model & data, render sidebar, route ke halaman yang dipilih. Tidak ada logika bisnis di sini. |
| `config.py` | Satu-satunya tempat untuk: path file, tema warna Plotly, dan mapping kategori (dominant category, pct category, frequency category). Ubah di sini kalau ada perubahan skema fitur. |
| `utils.py` | Fungsi kecil yang dipakai berulang: `format_idr`, `risk_badge`, `sanitize_columns`, `build_gauge_figure`, `df_download_button`. |
| `data_loader.py` | Semua pemanggilan file (pickle/CSV/Excel) dengan `@st.cache_resource` / `@st.cache_data`. |
| `item_classifier.py` | Klasifikasi kategori barang rental level-item (lihat catatan di README root). Murni untuk analitik, tidak memengaruhi fitur model. |
| `components.py` | Komponen tampilan HTML/CSS reusable (KPI card, header, gauge result, dsb). |
| `app_pages/*.py` | Satu file per halaman dashboard. Fungsi `render(...)` dipanggil dari `app.py`. |
| `style.css` | Stylesheet eksternal, di-inject via `components.load_css`. |

### Kenapa folder halaman bernama `app_pages/` bukan `pages/`?

Streamlit otomatis mendeteksi folder bernama `pages/` yang sejajar dengan
script utama sebagai fitur *multi-page app* bawaan (setiap file akan muncul
sebagai halaman terpisah di sidebar Streamlit). Dashboard ini sengaja pakai
navigasi custom (list di sidebar, lihat `components.render_sidebar_nav`)
supaya tampilan & pengelompokan halaman lebih terkontrol, sehingga folder
modulnya diberi nama `app_pages/` untuk menghindari konflik dengan fitur
otomatis tersebut.

## Navigasi Sidebar

Navigasi ditampilkan sebagai list (bukan dropdown), dikelompokkan per
kategori lewat `NAV_GROUPS` di `config.py`:

- **Ringkasan** — Overview
- **Analisis Data** — Analisis Churn, Data Explorer
- **Prediksi** — Prediksi Pelanggan

Halaman aktif disimpan di `st.session_state.current_page` dan dirender oleh
`components.render_sidebar_nav()`.

## Menambah Halaman Baru

1. Buat file baru di `app_pages/`, misal `app_pages/halaman_baru.py`, dengan
   fungsi `def render(...): ...`.
2. Import dan tambahkan routing di `app.py`.
3. Tambahkan label halaman ke grup yang sesuai di `NAV_GROUPS` (`config.py`).

## Menambah Kategori / Mapping Baru

Semua mapping kategori (dominant category, pct category, frequency category)
ada di `config.py`. Jangan duplikasi dict yang sama di file page lain — import
dari `config` supaya konsisten di seluruh halaman.

## Auto-update saat kode diubah

Konfigurasi ada di `dashboard/.streamlit/config.toml` (`runOnSave = true`).
Jalankan dari folder `dashboard/`: `streamlit run app.py`. Setiap file `.py` yang
disimpan langsung memuat ulang halaman. Cache data/model juga otomatis diperbarui
saat file CSV/pkl/Excel-nya berubah (kunci cache = waktu modifikasi file), jadi
setelah retrain tidak perlu clear cache manual. Bila di-deploy di Streamlit Cloud,
perubahan ter-update otomatis setiap ada push ke repository.

## Skor Risiko Gabungan (model + sinyal perilaku)

Persentase risiko pelanggan **Aktif** = skor model (out-of-fold) yang digabung dengan skor perilaku:
`skor_final = skor_model + (1 - skor_model) * 0.6 * skor_perilaku` (`utils.blend_risk`, bobot di `config.BEHAVIOR_WEIGHT`).
Skor perilaku (0-1) berasal dari jeda rata-rata antar order (30%), frekuensi order (20%), sisa masa kontrak (25%),
payment ratio (15%), dan porsi status SMS On Going (10%). Sinyal ini hanya bisa menaikkan skor, sehingga pelanggan
dengan alasan berwarna merah (mis. jeda order panjang) tidak lagi berskor 0%. Model dan file `.pkl` tidak berubah.
