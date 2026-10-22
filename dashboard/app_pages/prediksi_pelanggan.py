"""Halaman Prediksi Pelanggan - mode: cari pelanggan existing & input manual.

REVISI definisi churn (berbasis End Date kontrak):
- STATUS pelanggan existing ditentukan ATURAN, bukan model:
    * End Date terakhir < tanggal acuan  -> CHURN (semua kontrak sudah berakhir, risiko 100%)
    * End Date terakhir >= tanggal acuan -> AKTIF (pasti aktif)
- PERSENTASE RISIKO hanya bermakna untuk pelanggan AKTIF: skor model dari sinyal lain
  (status SMS Rental, status order, pembayaran, pola order, dll) yang digabung dengan
  skor perilaku (jeda order, frekuensi, sisa kontrak) - lihat utils.blend_risk. Untuk pelanggan existing
  dipakai skor out-of-fold (customer_risk_scores.csv) supaya tidak terlalu optimis.
- Fitur End Date & turunannya (recency, umur/rentang order pelanggan, overdue, tahun akuisisi)
  TIDAK dipakai model - lihat Preprocessing.ipynb Step 15 & 19 - sehingga form Input Manual
  juga tidak menanyakannya.
- Nilai kosong (NaN) di data asli tetap dikirim sebagai NaN ke model (bukan dipaksa 0).
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from components import (
    render_page_header, render_section_header, render_prediction_result,
    render_risk_recommendation, render_churn_reasons, render_winback_recommendation,
    render_crm_info,
)
from config import COLOR_CHURN, COLOR_ACTIVE, PLOTLY_LAYOUT
from utils import (
    sanitize_columns, format_idr, format_date_id, risk_badge, risk_level_label,
    build_gauge_figure, generate_churn_reasons, blend_risk,
)


def render(df_feat, model, feature_cols, test_raw):
    render_page_header(title="Prediksi Churn Pelanggan")

    pred_mode = st.radio("Mode Prediksi", [
        "🔎 Cari Pelanggan Existing",
        "📝 Input Manual",
        #"📁 Batch dari Data Test",
    ], horizontal=True)

    if pred_mode == "🔎 Cari Pelanggan Existing":
        _mode_search(df_feat, model, feature_cols)
    elif pred_mode == "📝 Input Manual":
        _mode_manual(df_feat, model, feature_cols)
    #else:
    #    _mode_batch(test_raw, model, feature_cols)


def _mode_search(df_feat, model, feature_cols):
    st.markdown("### Cari & Pilih Pelanggan")
    st.caption("Ketik nama di kotak ini untuk menyaring daftar, lalu pilih dari dropdown-nya.")
    all_names = sorted(df_feat["Customer"].dropna().unique().tolist())
    sel_name = st.selectbox(
        "Nama Pelanggan", all_names,
        index=None, placeholder="Ketik atau pilih nama pelanggan...",
    )
    if not sel_name:
        st.info(f"Ada {len(all_names)} pelanggan di database — mulai ketik nama untuk mencari.")
        return

    cust_row = df_feat[df_feat["Customer"] == sel_name].iloc[0]
    cust_idx = df_feat[df_feat["Customer"] == sel_name].index[0]

    san_df = sanitize_columns(df_feat)
    # Default NaN, bukan 0.0: kolom yang datanya memang kosong di database (mis. customer
    # one-time tanpa avg_gap_between_orders_days) tetap dikirim sebagai NaN ke model.
    input_dict = {c: np.nan for c in feature_cols}
    for c in feature_cols:
        if c in san_df.columns:
            val = san_df.loc[cust_idx, c]
            if pd.notna(val):
                try:
                    input_dict[c] = float(val)
                except (ValueError, TypeError):
                    pass

    # Sisa kontrak bukan fitur model, tapi dipakai untuk alasan & skor perilaku
    input_dict["days_to_contract_end"] = cust_row.get("days_to_contract_end", np.nan)

    try:
        actual_churn = int(cust_row.get("churn_flag", 0)) == 1
        prob = float(cust_row["risk_prob"])            # Churn = 1.0 (pasti); Aktif = skor model out-of-fold
        last_end = cust_row.get("last_end_date")
        n_running = int(cust_row.get("n_running_orders", 0))

        col_res, col_name = st.columns([1, 2])
        with col_res:
            if actual_churn:
                render_prediction_result("CHURN", prob, "🔴 Status pasti", is_churn=True,
                                         sub_text="Status pasti — seluruh kontrak sudah berakhir")
            else:
                render_prediction_result("AKTIF", prob, risk_badge(prob), is_churn=False,
                                         sub_text="Risiko churn (model + sinyal perilaku)")
        with col_name:
            st.markdown(f"#### 👤 {sel_name}")
            if actual_churn:
                st.caption(
                    f"Status **Churn**: kontrak terakhir berakhir **{format_date_id(last_end)}**. "
                    "Status ditentukan aturan End Date, bukan hasil prediksi model."
                )
            else:
                st.caption(
                    f"Status **Aktif** (pasti): masih ada **{n_running}** order berjalan; kontrak terakhir "
                    f"berakhir **{format_date_id(last_end)}**."
                )

        render_section_header("Opportunity & Notes (CRM)")
        render_crm_info(cust_row)

        st.markdown("<br>", unsafe_allow_html=True)
        icols = st.columns(4)
        kpis = [
            ("Total Order", f"{int(cust_row.get('total_orders', 0)):,}"),
            ("Total Invoiced", format_idr(cust_row.get('total_invoiced', 0))),
            ("Payment Ratio", f"{cust_row.get('payment_ratio_imputed', 0):.1f}%"),
            ("Kontrak Terakhir Berakhir", format_date_id(last_end)),
            ("Order Berjalan", f"{n_running:,}"),
            ("Rentang Order", f"{int(cust_row.get('order_span_days', 0)):,} hari"),
            ("Avg Lifetime (Lama Sewa)", f"{cust_row.get('avg_lifetime_days', 0):.1f} hari"),
            ("Outstanding", format_idr(cust_row.get('outstanding_balance', 0))),
        ]
        for i, (k, v) in enumerate(kpis):
            with icols[i % 4]:
                st.metric(k, v)

        if actual_churn:
            render_section_header("Rekomendasi Tindakan")
            render_winback_recommendation()
        else:
            st.plotly_chart(build_gauge_figure(prob, height=280), use_container_width=True)

            render_section_header("Alasan Hasil Prediksi")
            reasons = generate_churn_reasons(input_dict, prob)
            render_churn_reasons(reasons, risk_level_label(prob))

            render_section_header("Rekomendasi Tindakan")
            render_risk_recommendation(prob)

    except Exception as e:
        st.error(f"Gagal prediksi: {e}")


def _freq_category(order_freq):
    """Sama dengan binning di Preprocessing.ipynb Step 8 (order_frequency_per_month)."""
    if order_freq <= 0.25:
        return "rare"
    if order_freq <= 0.5:
        return "occasional"
    if order_freq <= 1.0:
        return "regular"
    return "frequent"


def _purchase_pattern(avg_gap):
    """Sama dengan purchase_pattern() di Preprocessing.ipynb Step 8."""
    if avg_gap <= 30:
        return "frequent"
    if avg_gap <= 90:
        return "regular"
    if avg_gap <= 180:
        return "occasional"
    return "rare"


def _mode_manual(df_feat, model, feature_cols):
    """Form input manual untuk pelanggan baru / skenario what-if.

    Yang ditanyakan hanya fitur yang benar-benar dipakai model. End Date, recency,
    umur/rentang order, overdue, dan tahun akuisisi tidak ditanyakan karena bukan fitur
    model (lihat Preprocessing.ipynb Step 15 & 19). Fitur turunan (kategori frekuensi,
    purchase pattern, dummy kategori produk, dsb) dihitung otomatis dari input
    dengan aturan yang sama seperti saat preprocessing.
    """
    st.markdown("### Input Data Pelanggan")
    st.caption(
        "Simulasi skor risiko churn dari sinyal yang benar-benar dipakai model. "
        "Hasilnya adalah **skor risiko**, bukan status — status pelanggan sungguhan "
        "ditentukan tanggal berakhir kontrak (End Date)."
    )

    cat_prefix = "dominant_product_category_"
    cat_options = [c[len(cat_prefix):] for c in feature_cols if c.startswith(cat_prefix)]

    with st.form("manual_form"):
        c1, c2 = st.columns(2, gap="large")
        with c1:
            st.markdown("**Riwayat Pelanggan**")
            total_orders = st.number_input("Total Order", min_value=1, value=3, step=1)
            avg_dur     = st.number_input("Rata-rata Lifetime / Lama Sewa (hari)", min_value=0.0, value=365.0, step=1.0)
            avg_gap     = st.number_input("Rata-rata Jeda Antar Order (hari)", min_value=0.0, value=90.0, step=1.0,
                                           help="Diabaikan bila Total Order = 1.")
            order_freq  = st.number_input("Order per Bulan (rata-rata)", min_value=0.0, value=0.3, step=0.05,
                                           help="Diabaikan bila Total Order = 1.")
            product_cat = st.selectbox("Kategori Barang Dominan", cat_options) if cat_options else None

        with c2:
            st.markdown("**Pembayaran & Status Order**")
            total_pv    = st.number_input("Total Project Value (Rp)", min_value=0.0, value=80000000.0, step=500000.0, format="%.0f")
            pay_ratio   = st.number_input("Payment Ratio (%)", min_value=0.0, max_value=100.0, value=90.0, step=0.5)
            pct_ongoing = st.number_input("% Order SMS On Going (Delivered)", min_value=0.0, max_value=1.0, value=0.6, step=0.05,
                                           help="Porsi order yang berstatus SMS 'On Going Delivered' (kontrak sedang berjalan).")
            pct_sms_c   = st.number_input("% Order SMS Confirmed Rental", min_value=0.0, max_value=1.0, value=0.2, step=0.05)
            pct_problem = st.number_input("% Order SMS Bermasalah (Expired/Unknown)", min_value=0.0, max_value=1.0, value=0.0, step=0.05)
            pct_closed  = st.number_input("% Order Berstatus Closed", min_value=0.0, max_value=1.0, value=0.0, step=0.05,
                                           help="Porsi order yang sudah berstatus Closed Rental.")

        submitted = st.form_submit_button("Hitung Skor Risiko", use_container_width=True)

    if not submitted:
        return

    # ── Turunan otomatis ────────────────────────────────────────────────
    avg_pv         = total_pv / max(total_orders, 1)
    total_invoiced = total_pv
    avg_invoiced   = avg_pv
    total_paid     = total_invoiced * (pay_ratio / 100.0)
    avg_paid       = total_paid / max(total_orders, 1)
    outstanding    = max(total_invoiced - total_paid, 0.0)
    one_time       = total_orders == 1
    pct_partial    = max(0.0, 1.0 - pct_ongoing - pct_sms_c - pct_problem)   # sisa dianggap On Going Partial

    input_d = {c: np.nan for c in feature_cols}
    input_d.update({
        "total_orders": float(total_orders),
        "unique_order_dates": float(total_orders),
        "total_invoiced": total_invoiced,
        "avg_invoiced": avg_invoiced,
        "invoiced_count": float(total_orders),
        "total_paid": total_paid,
        "avg_paid": avg_paid,
        "total_project_value": total_pv,
        "avg_project_value": avg_pv,
        "avg_lifetime_days": avg_dur,
        "order_frequency_per_month": np.nan if one_time else order_freq,
        "avg_gap_between_orders_days": np.nan if one_time else avg_gap,
        "payment_ratio": pay_ratio,
        "has_payment_data": 1.0,
        "payment_ratio_imputed": pay_ratio,
        "outstanding_balance": outstanding,
        "has_project_value": 1.0 if total_pv > 0 else 0.0,
        "is_one_time_customer": 1.0 if one_time else 0.0,
        # status order
        "pct_status_closed_rental": pct_closed,
        "pct_status_confirmed_rental": 1.0 - pct_closed,
        "pct_status_extension_review": 0.0,
        "confirmation_rate": 1.0 - pct_closed,
        # status SMS rental
        "pct_sms_on_going_delivered": pct_ongoing,
        "pct_sms_on_going_partial_delivery": pct_partial,
        "pct_sms_confirmed_rental": pct_sms_c,
        "pct_sms_unknown": pct_problem,
        "pct_sms_closed_rental": pct_closed,
        "pct_sms_expired_rent_on_going": 0.0,
        "pct_sms_expired_rent_returned_done": 0.0,
        "pct_sms_expired_rent_returned_partial": 0.0,
        "pct_sms_extension_review": 0.0,
        "pct_problematic_rental_state": pct_problem,
    })

    # Kategori frekuensi & purchase pattern (one-hot, sama dengan preprocessing)
    freq_cat = "one_time" if one_time else _freq_category(order_freq)
    pattern = "one_time" if one_time else _purchase_pattern(avg_gap)
    for c in feature_cols:
        if c.startswith("order_frequency_category_"):
            input_d[c] = 1.0 if c == f"order_frequency_category_{freq_cat}" else 0.0
        elif c.startswith("purchase_pattern_"):
            input_d[c] = 1.0 if c == f"purchase_pattern_{pattern}" else 0.0

    # Kategori produk: dummy dominan + persentase kategori (100% ke kategori terpilih)
    if product_cat is not None:
        for c in feature_cols:
            if c.startswith(cat_prefix):
                input_d[c] = 1.0 if c == f"{cat_prefix}{product_cat}" else 0.0
            elif c.startswith("pct_") and c.replace("pct_", "") in ("komputer_laptop", "lainnya", "mobil", "motor", "televisi"):
                key = product_cat.lower().replace("/", "_").replace(" ", "_")
                input_d[c] = 1.0 if c == f"pct_{key}" else 0.0

    try:
        X_in = pd.DataFrame([input_d])[feature_cols].values
        prob_model = float(model.predict_proba(X_in)[0, 1])
        prob = blend_risk(prob_model, input_d)   # model + sinyal perilaku (sama dengan Overview)

        cr1, cr2 = st.columns([1, 2])
        with cr1:
            render_prediction_result(f"RISIKO {risk_level_label(prob).upper()}", prob, risk_badge(prob),
                                     is_churn=(prob >= 0.5), sub_text="Skor risiko churn (simulasi)")
        with cr2:
            st.plotly_chart(build_gauge_figure(prob, height=260), use_container_width=True)

        render_section_header("Alasan Hasil Prediksi")
        reasons = generate_churn_reasons(input_d, prob)
        render_churn_reasons(reasons, risk_level_label(prob))

        render_risk_recommendation(prob)

    except Exception as e:
        st.error(f"Gagal prediksi: {e}")

'''
def _mode_batch(test_raw, model, feature_cols): 

    st.markdown("### Prediksi Batch dari Data Test")
    t_san = sanitize_columns(test_raw.copy())
    f_avail = [c for c in feature_cols if c in t_san.columns]
    X2 = t_san[f_avail]
    if "churn_flag" in X2.columns:
        X2 = X2.drop(columns=["churn_flag"])
    y2 = t_san["churn_flag"] if "churn_flag" in t_san.columns else None

    feat2 = [c for c in feature_cols if c in X2.columns]
    try:
        proba2 = model.predict_proba(X2[feat2])[:, 1]
        pred2 = model.predict(X2[feat2])

        res = pd.DataFrame({
            "No": range(1, len(proba2) + 1),
            "Probabilitas Churn (%)": (proba2 * 100).round(2),
            "Prediksi": ["Churn" if p == 1 else "Aktif" for p in pred2],
            "Risk Level": [risk_badge(p) for p in proba2],
        })
        if y2 is not None:
            res["Status Aktual"] = ["Churn" if y == 1 else "Aktif" for y in y2.values]

        flt = st.selectbox("Filter Prediksi", ["Semua", "Churn", "Aktif"])
        if flt == "Churn":
            res = res[res["Prediksi"] == "Churn"]
        elif flt == "Aktif":
            res = res[res["Prediksi"] == "Aktif"]
        res = res.sort_values("Probabilitas Churn (%)", ascending=False).reset_index(drop=True)

        m1, m2, m3 = st.columns(3)
        m1.metric("Total Data", len(res))
        m2.metric("Prediksi Churn", (res["Prediksi"] == "Churn").sum())
        m3.metric("Prediksi Aktif", (res["Prediksi"] == "Aktif").sum())

        st.dataframe(res.style.background_gradient(
            subset=["Probabilitas Churn (%)"], cmap="RdYlGn_r", vmin=0, vmax=100),
            use_container_width=True, height=420)

        st.download_button(
            "⬇️ Unduh Hasil Batch (CSV)",
            data=res.to_csv(index=False).encode("utf-8-sig"),
            file_name="hasil_prediksi_batch.csv",
            mime="text/csv",
        )

        fig_pd = px.histogram(res, x="Probabilitas Churn (%)", color="Prediksi",
            barmode="overlay", nbins=30, opacity=0.75,
            color_discrete_map={"Churn": COLOR_CHURN, "Aktif": COLOR_ACTIVE},
            title="Distribusi Probabilitas Prediksi Batch")
        fig_pd.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_pd, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
'''