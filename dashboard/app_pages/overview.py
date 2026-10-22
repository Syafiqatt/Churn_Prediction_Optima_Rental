"""Halaman Overview - ringkasan KPI utama & sekilas kondisi churn."""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import render_page_header, render_kpi_card, render_section_header
from config import PLOTLY_LAYOUT, COLOR_CHURN, COLOR_ACTIVE
from utils import risk_badge, format_idr, format_date_id


def render(df_feat, model, feature_cols):
    render_page_header(
        title="Dashboard Prediksi Churn Pelanggan Rental",
    )
    st.markdown("---")

    total      = len(df_feat)
    n_churn    = int(df_feat["churn_flag"].sum())
    n_active   = total - n_churn
    churn_rate = n_churn / total * 100
    avg_orders = df_feat["total_orders"].mean()
    avg_lt     = df_feat["order_span_days"].mean()

    c1, c2, c3, c4, c5 = st.columns(5)
    kpi_data = [
        (c1, "👥", f"{total:,}", "Total Pelanggan", "", ""),
        (c2, "🔴", f"{n_churn:,}", "Pelanggan Churn", f"{churn_rate:.1f}% · semua kontrak berakhir", "kpi-churn"),
        (c3, "🟢", f"{n_active:,}", "Pelanggan Aktif", f"{100 - churn_rate:.1f}% · masih ada kontrak berjalan", "kpi-active"),
        (c4, "📦", f"{avg_orders:.1f}", "Rata-rata Order", "per pelanggan", ""),
        (c5, "📅", f"{avg_lt:.0f}", "Avg Rentang Order", "hari per pelanggan", ""),
    ]
    for col, icon, val, label, sub, extra in kpi_data:
        with col:
            render_kpi_card(icon, val, label, sub, extra)


    st.markdown("<br>", unsafe_allow_html=True)

    # Panduan membaca skor risiko
    with st.expander("📖 Panduan: Cara Membaca Risiko Churn", expanded=False):
        st.markdown("""
        **Status** (Aktif / Churn) ditentukan oleh **tanggal berakhir kontrak (End Date)** pada tanggal acuan:
        - **Churn** — End Date terakhir pelanggan sudah lewat (sebelum tanggal acuan): seluruh kontraknya sudah habis. Status ini pasti (risiko 100%).
        - **Aktif** — End Date terakhir pelanggan pada/sesudah tanggal acuan: masih ada kontrak berjalan. Status ini pasti aktif.

        **Persentase risiko** hanya dihitung untuk pelanggan **Aktif**, dari skor model (status SMS Rental, status order,
        pembayaran, pola order) yang digabung dengan sinyal perilaku (jeda antar order, frekuensi order, sisa masa kontrak,
        payment ratio). Sinyal perilaku hanya bisa menaikkan skor, sehingga pelanggan dengan jeda order panjang tidak lagi
        berskor 0%. Skor ini dipakai untuk menentukan prioritas tindak lanjut
        perpanjangan kontrak. Persentase **bukan** penentu status.

        | Skor Risiko | Level Risiko | Rekomendasi |
        |---|---|---|
        | **≥ 70%** | 🔴 Tinggi | Hubungi dalam 24-48 jam, assign account manager, tawarkan solusi |
        | **40 - 70%** | 🟡 Sedang | Pantau transaksi 2 minggu, kirim survei kepuasan |
        | **< 40%** | 🟢 Rendah | Layani seperti biasa, kandidat referral |
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 2
    col_a, col_b = st.columns([1, 2])
    with col_a:
        render_section_header("📊 Distribusi Status Pelanggan")
        pie_fig = go.Figure(go.Pie(
            labels=["Churn", "Aktif"], values=[n_churn, n_active], hole=0.55,
            marker=dict(colors=[COLOR_CHURN, COLOR_ACTIVE], line=dict(color="#ffffff", width=2)),
            textinfo="percent+label", textfont=dict(size=13, color="white"),
        ))
        pie_fig.update_layout(**PLOTLY_LAYOUT,
            annotations=[dict(text=f"<b>{churn_rate:.1f}%</b><br>Churn",
                               font=dict(size=14, color="#0f172a"), showarrow=False)])
        st.plotly_chart(pie_fig, use_container_width=True)

    with col_b:
        render_section_header("💰 Rata-rata Revenue per Status")
        df_rev = df_feat.groupby("churn_label").agg(
            avg_invoiced=("total_invoiced", "mean"),
            avg_paid=("total_paid", "mean"),
            avg_outstanding=("outstanding_balance", "mean"),
        ).reset_index()
        df_rev_melt = df_rev.melt(id_vars="churn_label", var_name="Metrik", value_name="Nilai")
        fig_rev = px.bar(df_rev_melt, x="Metrik", y="Nilai", color="churn_label",
                         barmode="group",
                         color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                         title="Perbandingan Financial Metrics",
                         labels={"Nilai": "Rp", "Metrik": "", "churn_label": "Status"})
        fig_rev.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_rev, use_container_width=True)

    # Row 3
    col_c, col_d = st.columns(2)
    with col_c:
        render_section_header("📈 Distribusi Total Order")
        fig_box = px.box(df_feat, x="churn_label", y="total_orders", color="churn_label",
                         color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                         labels={"churn_label": "Status", "total_orders": "Jumlah Order"})
        fig_box.update_layout(**PLOTLY_LAYOUT, showlegend=False,
                              title="Distribusi Total Order per Status")
        st.plotly_chart(fig_box, use_container_width=True)

    with col_d:
        render_section_header("📅 Distribusi Rentang Order")
        fig_hist = px.histogram(df_feat, x="order_span_days", color="churn_label",
                                barmode="overlay", nbins=40, opacity=0.75,
                                color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                                labels={"order_span_days": "Rentang Order (hari)", "churn_label": "Status"})
        fig_hist.update_layout(**PLOTLY_LAYOUT, title="Distribusi Rentang Order Pelanggan (hari)")
        st.plotly_chart(fig_hist, use_container_width=True)

    # Row 4: Payment ratio scatter + Top pelanggan berisiko tinggi
    # (chart akuisisi-per-tahun dipindah ke tab "Temporal" pada halaman
    #  Analisis Churn supaya tidak duplikat; slot ini diganti dengan
    #  watchlist yang lebih actionable untuk tim retensi)
    render_section_header("💳 Outstanding Balance per Kelompok Payment Ratio")
    pr_bins = df_feat.copy()
    pr_bins["pr_bucket"] = pd.cut(
        pr_bins["payment_ratio_imputed"], bins=[-0.01, 25, 50, 75, 100],
        labels=["0-25%", "25-50%", "50-75%", "75-100%"],
    )
    pr_grp = pr_bins.groupby(["pr_bucket", "churn_label"], observed=True)["outstanding_balance"] \
        .mean().reset_index()
    fig_pr = px.bar(pr_grp, x="pr_bucket", y="outstanding_balance", color="churn_label",
                     barmode="group",
                     color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                     labels={"pr_bucket": "Payment Ratio", "outstanding_balance": "Rata-rata Outstanding (Rp)",
                             "churn_label": "Status"})
    fig_pr.update_layout(**PLOTLY_LAYOUT, title="Rata-rata Outstanding Balance per Kelompok Payment Ratio")
    st.plotly_chart(fig_pr, use_container_width=True)
    st.caption("Semakin rendah payment ratio, semakin tinggi rata-rata outstanding balance-nya.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Row 5: Watchlist risiko churn - tertinggi & terendah berdampingan supaya
    # tim retensi lihat dua ujung spektrum sekaligus (bukan cuma yang tertinggi).
    st.markdown("<br>", unsafe_allow_html=True)
    st.info("💡 Watchlist hanya berisi customer berstatus **Aktif** (masih ada kontrak berjalan), "
            "diurutkan menurut skor risiko gabungan (model out-of-fold + sinyal perilaku seperti jeda order, "
            "frekuensi, sisa kontrak, dan pembayaran).")

    col_g, col_h = st.columns(2)
    active_df = df_feat[df_feat["churn_flag"] == 0].copy()

    def _render_watchlist(col, header, subset_df, caption):
        with col:
            render_section_header(header)
            show = subset_df[["Customer", "total_orders", "avg_gap_between_orders_days", "total_invoiced", "last_end_date", "risk_prob"]].copy()
            show["risk_prob"] = (show["risk_prob"] * 100).round(1)
            show["Level Risiko"] = show["risk_prob"].apply(lambda x: risk_badge(x / 100))
            show["Kontrak Berakhir"] = show["last_end_date"].apply(format_date_id)
            show = show.rename(columns={"Customer": "Pelanggan", "total_orders": "Order",
                                        "total_invoiced": "Invoiced", "risk_prob": "Risiko%",
                                        "avg_gap_between_orders_days": "Jeda Order (hari)"})
            show["Jeda Order (hari)"] = show["Jeda Order (hari)"].round(0)
            show = show[["Pelanggan", "Order", "Jeda Order (hari)", "Invoiced", "Kontrak Berakhir", "Risiko%", "Level Risiko"]]
            show["Invoiced"] = show["Invoiced"].apply(format_idr)
            show.index = range(1, len(show) + 1)

            st.dataframe(
                show.style.background_gradient(subset=["Risiko%"], cmap="Reds", vmin=0, vmax=100).format({"Risiko%": lambda v: "<0.1%" if v < 0.1 else f"{v:.1f}%", "Jeda Order (hari)": "{:.0f}"}, na_rep="-"),
                use_container_width=True, height=360,
            )
            st.caption(caption)

    top_risk = active_df.sort_values("risk_prob", ascending=False).head(10)
    low_risk = active_df.sort_values("risk_prob", ascending=True).head(10)
    _render_watchlist(col_g, "🚨 Top 10 Customer Aktif — Skor Risiko Tertinggi", top_risk,
                       "Prioritas tindak lanjut perpanjangan kontrak.")
    _render_watchlist(col_h, "🛡️ Top 10 Customer Aktif — Skor Risiko Terendah", low_risk,
                       "Customer paling stabil, cocok jadi kandidat referral.")
