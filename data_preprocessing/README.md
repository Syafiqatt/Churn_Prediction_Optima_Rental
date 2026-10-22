# Data Preprocessing — Detail Pipeline

`src/Preprocessing.ipynb` mengubah data transaksi mentah (`data/raw/Data-Mentah-Rental-Order.xlsx`,
2.262 order aktif dari 611 customer, Okt 2021–Agu 2026) menjadi fitur level-customer siap-model,
lewat 22 step:

1. Load Data — baca Excel mentah, validasi skema kolom wajib.
2. Identify Main Rows vs Child Rows — pisahkan baris order utama vs baris item/produk.
3. Data Cleaning — parsing tanggal, standarisasi nama customer, isi `SMS Rental State` kosong.
4. Separate Draft Segment — pisahkan quotation (`Status == 'Draft'`) dari order aktif/closed.
5. Product Category Extraction — kategori barang dari nama customer (lihat catatan di README utama).
6. Calculate Churn Label — End Date terakhir pelanggan `< REFERENCE_DATE` (29 Sep 2026) -> Churn; `>=` -> Aktif.
7. Rental Duration Features — lifetime sewa terencana & flag overdue.
8. Customer-Level Feature Engineering — agregasi ke level customer (total order, rentang order, lifetime sewa, dll).
9. Product Category Features — kategori dominan + breakdown persentase per customer.
10. Temporal / Seasonality Features — bulan/kuartal/tahun order pertama, volume akuisisi per tahun.
11. SMS Rental State Distribution — distribusi status SMS per customer.
12. Order Status Distribution — distribusi status order per customer.
13. Draft Segment Summary — ringkasan segmen draft + flag orphan customer.
14. Missing Value Strategy — kebijakan eksplisit per kolom (tidak ada mean/median-impute diam-diam).
15. Drop Leakage Columns — buang kolom leakage dari CSV; tandai kolom penentu label (`last_end_date`, `days_to_contract_end`, `n_running_orders`) yang hanya untuk tampilan.
16. Categorical Encoding — one-hot encode kolom kategorikal.
17. Numeric Data Validation — pengecekan konsistensi data (assert, bukan silent pass).
18. Feature Selection Recommendation — ranking korelasi fitur ke label (referensi, tidak otomatis dibuang).
19. Train/Test Split — stratified 80/20; di sini kolom penentu label dan fitur yang bisa
    merekonstruksi End Date (lihat revisi di bawah) dikeluarkan khusus dari matriks fitur model.
20. Scaling — `StandardScaler` di-fit di train saja, diterapkan ke test.
21. Save All Outputs — tulis 7 file ke `data/processed/`.
22. Summary — ringkasan akhir pipeline.

## Revisi: definisi churn berbasis End Date

Definisi lama (`days_since_last_order >= 180`) salah menandai pelanggan yang order terakhirnya
lama tapi kontraknya masih berjalan (median durasi kontrak ~3 tahun) sebagai churn. Dari 611
pelanggan, 303 di antaranya ternyata masih punya kontrak berjalan pada 29 Sep 2026.

Aturan baru (Step 6), `REFERENCE_DATE = 2026-09-29`:

- End Date terakhir pelanggan **<** `REFERENCE_DATE` -> **Churn** (195 pelanggan).
- End Date terakhir pelanggan **>=** `REFERENCE_DATE` -> **Aktif** (416 pelanggan).

Perbandingan tanggal memakai tanggal saja (jam diabaikan), dan End Date yang dipakai adalah yang
terbesar dari semua order non-draft pelanggan. Ubah `REFERENCE_DATE` di sel konfigurasi (atau
pakai `pd.Timestamp.today().normalize()`) saat data di-refresh, lalu jalankan ulang notebook.

Kolom baru di `customer_churn_features.csv`: `last_end_date`, `days_to_contract_end` (negatif =
sudah berakhir), `n_running_orders`. Ketiganya identik dengan label (AUC = 1.0, dicek di Step 15),
jadi hanya untuk tampilan dan **tidak pernah masuk fitur model** (dijaga `assert` di Step 19).

### Fitur yang dikeluarkan dari matriks fitur model (Step 19)

Bukan hanya kolom End Date, tapi juga fitur yang bersama-sama bisa menebak End Date:

- `customer_age_months`, `order_span_days`, `order_span_quartile_*`: recency = age*30 - rentang order,
  dan recency + lifetime sewa ~ End Date (tebakan sederhana ini sudah AUC 0.88, dicek di Step 15).
- `pct_overdue_rentals`: dihitung dari End Date vs tanggal acuan.
- `first_order_month/quarter/year`, `acquisition_year_volume`: fitur kohort tanggal yang bersama
  lifetime sewa ikut menebak End Date.

Fitur SMS Rental State, status order, pembayaran, dan pola order tetap dipakai model.

## Cara membaca performa model

ROC-AUC test set (~0.98) tinggi karena label ditentukan End Date dan fitur seperti lifetime sewa,
penagihan, dan status SMS ikut mencerminkan progres kontrak. Itu mengukur kemiripan dengan pelanggan
yang kontraknya sudah habis, bukan kemampuan memprediksi masa depan. Estimasi yang lebih jujur ada di
`modelling/modelling.ipynb` Step 10 (backtest point-in-time: dari pelanggan yang kontraknya habis
dalam 180 hari, siapa yang tidak memperpanjang): ROC-AUC ~0.69-0.71.

23. Informasi Opportunity & Notes CRM — filter Rental, isi Company Name kosong dari Customer/Name, ganti SYNAPS, cocokkan ke pelanggan (`customer_crm_info.csv`).
