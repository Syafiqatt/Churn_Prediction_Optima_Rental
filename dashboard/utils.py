"""
Utils - Fungsi bantu kecil yang dipakai di banyak halaman.
Sebelumnya beberapa fungsi ini (terutama gauge chart) diduplikasi
3x langsung di app.py; sekarang cukup satu implementasi di sini.
"""
import re

import pandas as pd
import plotly.graph_objects as go

import numpy as np

from config import PLOTLY_LAYOUT, BEHAVIOR_WEIGHT


def sanitize_columns(df):
    """Bersihkan nama kolom supaya aman dipakai sebagai identifier (LightGBM dsb)."""
    df = df.copy()
    df.columns = [re.sub(r"[^A-Za-z0-9_]", "_", c) for c in df.columns]
    return df


def _lin(x, good, bad):
    """Skala linear 0-1: 0 di titik 'good' (aman), 1 di titik 'bad' (berisiko). Berlaku dua arah."""
    return float(np.clip((x - good) / (bad - good), 0.0, 1.0))


def behavior_risk(feat):
    """Skor risiko perilaku 0-1 dari sinyal yang sama dengan alasan di dashboard.

    feat: dict / Series berisi nilai fitur pelanggan. Komponen yang datanya tidak
    tersedia (mis. sisa kontrak di Input Manual) dilewati dan bobotnya dinormalisasi.
    Jeda order & frekuensi yang kosong (pelanggan 1x order) dinilai netral-cenderung
    berisiko (0.5) karena belum ada pola pemesanan berulang.
    """
    def g(k):
        v = feat.get(k) if hasattr(feat, "get") else None
        return None if v is None or pd.isna(v) else float(v)

    parts = []  # (bobot, skor 0-1)

    gap = g("avg_gap_between_orders_days")
    parts.append((0.30, 0.5 if gap is None else _lin(gap, 60, 365)))

    freq = g("order_frequency_per_month")
    parts.append((0.20, 0.5 if freq is None else _lin(freq, 0.5, 0.1)))

    dte = g("days_to_contract_end")
    if dte is not None:
        parts.append((0.25, _lin(dte, 365, 90)))

    pr = g("payment_ratio_imputed")
    if pr is None:
        pr = g("payment_ratio")
    if pr is not None:
        parts.append((0.15, _lin(pr, 80, 50)))

    if g("pct_sms_on_going_delivered") is not None:
        ongoing = (g("pct_sms_on_going_delivered") or 0) + (g("pct_sms_on_going_partial_delivery") or 0)
        parts.append((0.10, _lin(ongoing, 0.6, 0.1)))

    total_w = sum(w for w, _ in parts)
    return sum(w * s for w, s in parts) / total_w if total_w else 0.0


def blend_risk(model_prob, feat):
    """Gabungkan skor model dengan skor perilaku. Skor perilaku hanya bisa menaikkan risiko."""
    b = behavior_risk(feat)
    return float(model_prob + (1.0 - model_prob) * BEHAVIOR_WEIGHT * b)


def ensure_risk_scores(df_feat, model, feature_cols):
    """Pastikan kolom risk_prob tersedia.

    - risk_prob_model : skor model (out-of-fold dari customer_risk_scores.csv; kalau file itu
      tidak ada, dihitung langsung dari model - lebih optimis karena model sudah pernah
      melihat pelanggan tersebut saat training).
    - risk_prob       : risiko final yang ditampilkan. Pelanggan Churn = 1.0 (status pasti,
      semua kontrak sudah berakhir); pelanggan Aktif = skor model
      yang digabung dengan skor perilaku (jeda order, frekuensi, sisa kontrak, pembayaran,
      status SMS) lewat blend_risk supaya konsisten dengan alasan yang ditampilkan.
    """
    df = df_feat.copy()
    if "risk_prob_model" not in df.columns or df["risk_prob_model"].isna().all():
        san = sanitize_columns(df)
        avail = [c for c in feature_cols if c in san.columns]
        df["risk_prob_model"] = model.predict_proba(san[avail].values)[:, 1]
    df["risk_behavior"] = df.apply(behavior_risk, axis=1)
    blended = df["risk_prob_model"] + (1.0 - df["risk_prob_model"]) * BEHAVIOR_WEIGHT * df["risk_behavior"]
    df["risk_prob"] = blended.where(df["churn_flag"] == 0, 1.0)
    return df


def format_date_id(ts):
    """Format tanggal Indonesia singkat, mis. 2026-09-29 -> '29 Sep 2026'."""
    if pd.isna(ts):
        return "-"
    bulan = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]
    return f"{ts.day} {bulan[ts.month - 1]} {ts.year}"


def format_idr(val):
    """Format angka ke format Rupiah, mis. 1500000 -> 'Rp 1.500.000'."""
    if pd.isna(val):
        return "Rp 0"
    return "Rp {:,.0f}".format(val).replace(",", ".")


def risk_badge(prob):
    """Label risiko churn berbasis threshold probabilitas."""
    if prob >= 0.70:
        return "🔴 Tinggi"
    elif prob >= 0.40:
        return "🟡 Sedang"
    return "🟢 Rendah"


def risk_level_label(prob):
    """Label risiko churn tanpa emoji (Tinggi/Sedang/Rendah), dipakai untuk teks alasan."""
    if prob >= 0.70:
        return "Tinggi"
    elif prob >= 0.40:
        return "Sedang"
    return "Rendah"


def generate_churn_reasons(feat, prob):
    """Menyusun daftar alasan di balik level risiko churn (Tinggi/Sedang/Rendah),
    berdasarkan nilai fitur pelanggan yang dipakai model (feat = dict fitur input).

    Setiap alasan berupa tuple (polarity, teks), polarity salah satu dari
    'negative' (mendorong risiko naik), 'positive' (mendorong risiko turun),
    atau 'neutral' (nilai sedang, tidak terlalu menentukan).
    Urutan akhir disesuaikan dengan level risiko: alasan negatif didahulukan
    untuk risiko Tinggi, alasan positif didahulukan untuk risiko Rendah.
    """
    def g(*keys, default=None):
        for k in keys:
            if k in feat and feat[k] is not None:
                return feat[k]
        return default

    reasons = []

    # Status SMS Rental / status order: proporsi order yang masih berjalan vs sudah selesai
    ongoing = (g("pct_sms_on_going_delivered", default=0) or 0) + (g("pct_sms_on_going_partial_delivery", default=0) or 0)
    if g("pct_sms_on_going_delivered") is not None:
        if ongoing >= 0.6:
            reasons.append(("positive", f"Sebagian besar order ({ongoing:.0%}) berstatus SMS On Going — kontrak masih berjalan aktif."))
        elif ongoing <= 0.1:
            reasons.append(("negative", f"Hampir tidak ada order berstatus SMS On Going ({ongoing:.0%}) — profilnya mirip pelanggan yang kontraknya sudah selesai."))
        else:
            reasons.append(("neutral", f"Order berstatus SMS On Going berada di level menengah ({ongoing:.0%})."))

    closed = g("pct_status_closed_rental")
    if closed is not None:
        if closed >= 0.6:
            reasons.append(("negative", f"Mayoritas order ({closed:.0%}) sudah berstatus Closed — kontrak-kontraknya banyak yang sudah selesai."))
        elif closed <= 0.1:
            reasons.append(("positive", f"Hampir semua order masih Confirmed/berjalan (Closed hanya {closed:.0%})."))

    problem = g("pct_problematic_rental_state")
    if problem is not None and problem >= 0.3:
        reasons.append(("negative", f"Porsi order dengan status SMS bermasalah (Expired/Unknown) cukup besar ({problem:.0%})."))

    # Payment ratio (0-100)
    pr = g("payment_ratio_imputed", "payment_ratio")
    if pr is not None:
        if pr >= 80:
            reasons.append(("positive", f"Payment ratio tinggi ({pr:.0f}%) — riwayat pembayaran pelanggan lancar."))
        elif pr <= 50:
            reasons.append(("negative", f"Payment ratio rendah ({pr:.0f}%) — banyak tagihan belum terbayar penuh."))
        else:
            reasons.append(("neutral", f"Payment ratio berada di level menengah ({pr:.0f}%)."))

    # Jeda rata-rata antar order
    gap = g("avg_gap_between_orders_days")
    if gap is not None:
        if gap <= 60:
            reasons.append(("positive", f"Jeda rata-rata antar order pendek (~{gap:.0f} hari) — pelanggan masih rutin bertransaksi."))
        elif gap >= 150:
            reasons.append(("negative", f"Jeda rata-rata antar order panjang (~{gap:.0f} hari) — pelanggan mulai jarang bertransaksi."))

    # Sisa masa kontrak
    dte = g("days_to_contract_end")
    if dte is not None:
        if dte <= 120:
            reasons.append(("negative", f"Kontrak terakhir berakhir dalam {dte:.0f} hari — saatnya menawarkan perpanjangan."))

    # Frekuensi order per bulan
    freq = g("order_frequency_per_month")
    if freq is not None:
        if freq >= 0.5:
            reasons.append(("positive", f"Frekuensi order cukup tinggi (~{freq:.2f}x per bulan)."))
        elif freq <= 0.1:
            reasons.append(("negative", f"Frekuensi order rendah (~{freq:.2f}x per bulan) — jarang melakukan order baru."))

    # Outstanding balance relatif terhadap total invoiced
    outstanding = g("outstanding_balance")
    invoiced = g("total_invoiced")
    if outstanding is not None and invoiced:
        ratio_out = outstanding / invoiced if invoiced else 0
        if ratio_out >= 0.3:
            reasons.append(("negative", f"Outstanding balance masih besar (±{ratio_out:.0%} dari total invoiced)."))
        elif ratio_out == 0:
            reasons.append(("positive", "Tidak ada outstanding balance — seluruh tagihan sudah lunas."))

    # Total order sebagai indikator loyalitas
    total_orders = g("total_orders")
    if total_orders is not None:
        if total_orders == 1:
            reasons.append(("negative", "Baru melakukan 1x order — belum ada pola pemesanan berulang yang terbentuk."))
        elif total_orders >= 5:
            reasons.append(("positive", f"Sudah melakukan {int(total_orders)}x order — pola pemesanan berulang yang cukup kuat."))

    # Urutkan sesuai level risiko: negatif dulu untuk risiko tinggi, positif dulu untuk risiko rendah
    if prob >= 0.70:
        order = {"negative": 0, "neutral": 1, "positive": 2}
    elif prob < 0.40:
        order = {"positive": 0, "neutral": 1, "negative": 2}
    else:
        order = {"negative": 0, "positive": 1, "neutral": 2}
    reasons.sort(key=lambda r: order.get(r[0], 3))

    # Batasi 5 alasan, tapi alasan negatif (merah) tidak boleh terpotong, termasuk untuk risiko Rendah
    if len(reasons) > 5:
        negs = [r for r in reasons if r[0] == "negative"][:5]
        others = [r for r in reasons if r[0] != "negative"][:5 - len(negs)]
        keep = set(map(id, negs + others))
        reasons = [r for r in reasons if id(r) in keep]
    return reasons


def build_gauge_figure(prob, height=280):
    """Gauge chart probabilitas churn (dipakai di 3 mode Prediksi Pelanggan)."""
    color = "#ef4444" if prob >= 0.5 else "#29823e"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob * 100,
        title={"text": "Probabilitas Churn (%)", "font": {"color": "#154a24", "size": 15}},
        number={"suffix": "%", "font": {"color": color, "size": 34}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#475569"},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#f1f5f9",
            "steps": [
                {"range": [0, 40], "color": "rgba(106,187,58,0.15)"},
                {"range": [40, 70], "color": "rgba(245,158,11,0.15)"},
                {"range": [70, 100], "color": "rgba(239,68,68,0.15)"},
            ],
            "threshold": {"line": {"color": "#154a24", "width": 3}, "value": prob * 100},
        },
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=height)
    return fig


def df_download_button(st, df, label, filename):
    """Tombol download DataFrame sebagai CSV (dipakai di Data Explorer)."""
    csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )
