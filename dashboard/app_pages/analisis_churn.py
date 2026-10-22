"""Halaman Analisis Churn - eksplorasi mendalam per dimensi."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components import render_page_header, render_section_header
from config import (
    PLOTLY_LAYOUT, COLOR_CHURN, COLOR_ACTIVE, RISK_SCALE,
    DOMINANT_CATEGORY_COLS, PCT_CATEGORY_COLS, FREQ_DISPLAY_LABELS, MONTH_LABELS,
)


def render(df_feat, item_df, stock_df=None):
    render_page_header(title="Analisis Mendalam Churn Pelanggan")

    tab1, tab2, tab3, tab4 = st.tabs([
        "💰 Revenue & Payment",
        "📦 Produk & Kategori",
        "🧾 Barang Rental (Detail)",
        "📅 Temporal",
        #"⚠️ Risiko Operasional",
    ])

    with tab1:
        _tab_revenue(df_feat)
    with tab2:
        _tab_produk_kategori(df_feat)
    with tab3:
        _tab_barang_rental(item_df, stock_df)
    with tab4:
        _tab_temporal(df_feat)
    #with tab5:
    #    _tab_risiko(df_feat)


def _tab_revenue(df_feat):
    col1, col2 = st.columns(2)
    with col1:
        fig_bal = px.box(df_feat, x="churn_label", y="outstanding_balance", color="churn_label",
                         color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                         title="Outstanding Balance per Status",
                         labels={"outstanding_balance": "Outstanding Balance (Rp)", "churn_label": "Status"})
        fig_bal.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        st.plotly_chart(fig_bal, use_container_width=True)

    with col2:
        fig_pr = px.box(df_feat, x="churn_label", y="payment_ratio_imputed", color="churn_label",
                        color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                        title="Payment Ratio per Status",
                        labels={"payment_ratio_imputed": "Payment Ratio (%)", "churn_label": "Status"})
        fig_pr.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        st.plotly_chart(fig_pr, use_container_width=True)


def _tab_produk_kategori(df_feat):
    st.caption(
        "Kategori di tab ini adalah fitur **level-pelanggan** yang dipakai model "
        "prediksi (diturunkan dari nama pelanggan). Untuk rincian barang yang "
        "benar-benar disewa per unit, lihat tab **Barang Rental (Detail)**."
    )
    cat_cols   = list(PCT_CATEGORY_COLS.values())
    cat_labels = list(PCT_CATEGORY_COLS.keys())
    cat_cols   = [c for c in cat_cols if c in df_feat.columns]

    df_cat = df_feat.groupby("churn_label")[cat_cols].mean()
    df_cat.columns = cat_labels[:len(cat_cols)]

    col1, col2 = st.columns(2)
    with col1:
        fig_radar = go.Figure()
        for status, color in [("Churn", COLOR_CHURN), ("Active", COLOR_ACTIVE)]:
            if status in df_cat.index:
                vals = df_cat.loc[status].tolist()
                labels_r = df_cat.columns.tolist()
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=labels_r + [labels_r[0]],
                    fill="toself", name=status, line_color=color,
                ))
        fig_radar.update_layout(**PLOTLY_LAYOUT,
            polar=dict(bgcolor="#f8fafc",
                       radialaxis=dict(visible=True, gridcolor="#e2e8f0"),
                       angularaxis=dict(gridcolor="#e2e8f0")),
            title="Profil Produk: Churn vs Aktif")
        st.plotly_chart(fig_radar, use_container_width=True)

    with col2:
        df_cat_plot = df_cat.T.reset_index()
        df_cat_plot.columns.name = None
        df_melt = df_cat_plot.melt(id_vars="index", var_name="Status", value_name="Pct")
        fig_bar_cat = px.bar(df_melt, x="index", y="Pct", color="Status", barmode="group",
                              color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                              title="Porsi Kategori Produk per Status",
                              labels={"index": "Kategori", "Pct": "Rata-rata Porsi"})
        fig_bar_cat.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_bar_cat, use_container_width=True)

    # Churn rate by dominant category
    df_dom = df_feat.copy()
    df_dom["dominant_category"] = "Unknown"
    for col_key, label_val in DOMINANT_CATEGORY_COLS.items():
        if col_key in df_dom.columns:
            mask = df_dom[col_key].isin([True, 1, "True", "1"])
            df_dom.loc[mask, "dominant_category"] = label_val

    churn_cat = df_dom.groupby("dominant_category")["churn_flag"].agg(["sum", "count"]).reset_index()
    churn_cat.columns = ["Kategori", "Churn", "Total"]
    churn_cat["Churn Rate (%)"] = (churn_cat["Churn"] / churn_cat["Total"] * 100).round(1)

    render_section_header("Churn Rate per Kategori Dominan")
    fig_cr = px.bar(churn_cat, x="Kategori", y="Churn Rate (%)", color="Churn Rate (%)",
                     color_continuous_scale=RISK_SCALE, text="Churn Rate (%)")
    fig_cr.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_cr.update_layout(**PLOTLY_LAYOUT, showlegend=False, coloraxis_showscale=False)
    st.plotly_chart(fig_cr, use_container_width=True)


def _tab_barang_rental(item_df, stock_df=None):
    """Breakdown LENGKAP barang rental langsung dari nama unit yang disewa,
    tanpa numpuk semua ke 'Lainnya' — semua kategori barang ditampilkan.
    Jika data stok (master produk) tersedia, jumlah stok per kategori
    ditampilkan berdampingan dengan jumlah order — keduanya sumber berbeda
    (stok = fisik saat ini, order = riwayat transaksi per pelanggan) jadi
    tidak digabung jadi satu angka."""
    if item_df is None or "item_category" not in item_df.columns:
        st.warning("Data detail order (orders_churn_detailed.csv) tidak ditemukan, "
                   "breakdown barang rental tidak dapat ditampilkan.")
        return

    st.caption(
        "Kategori di sini diturunkan langsung dari nama barang yang disewa "
        "('Rental Serial Lines/Product'), bukan dari nama pelanggan — sehingga "
        "seluruh jenis barang tampil apa adanya, bukan ditumpuk ke 'Lainnya'."
    )

    cat_count = item_df["item_category"].value_counts().reset_index()
    cat_count.columns = ["Kategori Barang", "Jumlah Order"]

    n_total = len(item_df)
    n_unknown = int((item_df["item_category"] == "Lainnya (Belum Teridentifikasi)").sum())
    m1, m2 = st.columns(2)
    m1.metric("Total Order dengan Data Barang", f"{n_total:,}")
    m2.metric("Jumlah Kategori Terdeteksi", f"{cat_count.shape[0]:,}")
    #m3.metric("Belum Teridentifikasi", f"{n_unknown:,} ({n_unknown/n_total*100:.1f}%)")

    col1, col2 = st.columns([1, 1])
    with col1:
        render_section_header("Distribusi Seluruh Kategori Barang")
        cat_count_sorted = cat_count.sort_values("Jumlah Order", ascending=True)
        fig_bar = px.bar(
            cat_count_sorted, 
            y="Kategori Barang", 
            x="Jumlah Order", 
            orientation="h",
            color="Kategori Barang",
            text="Jumlah Order"
        )
        fig_bar.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

    with col2:
        render_section_header("Churn Rate per Kategori Barang")
        if "churn_flag" in item_df.columns:
            cr = item_df.groupby("item_category")["churn_flag"].agg(["sum", "count"]).reset_index()
            cr.columns = ["Kategori Barang", "Churn", "Total"]
            cr["Churn Rate (%)"] = (cr["Churn"] / cr["Total"] * 100).round(1)
            cr = cr.sort_values("Churn Rate (%)", ascending=False)
            fig_cr2 = px.bar(cr, x="Kategori Barang", y="Churn Rate (%)", color="Churn Rate (%)",
                              color_continuous_scale=RISK_SCALE, text="Churn Rate (%)")
            fig_cr2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
            fig_cr2.update_layout(**PLOTLY_LAYOUT, showlegend=False, coloraxis_showscale=False,
                                   xaxis_tickangle=-30)
            st.plotly_chart(fig_cr2, use_container_width=True)
        else:
            st.info("Kolom churn_flag tidak tersedia di data detail order.")

    cat_count["Persentase Order (%)"] = (cat_count["Jumlah Order"] / n_total * 100).round(2)

    if stock_df is not None and not stock_df.empty:
        n_stok = int(stock_df["Jumlah Stok (On Hand)"].sum())
        st.markdown("---")
        render_section_header("Stok Barang Saat Ini (Master Produk)")
        st.caption(
            "Jumlah unit fisik yang tersedia per kategori, dari data master produk "
            "(bukan riwayat order) — jadi tidak dikaitkan dengan churn_flag pelanggan."
        )
        s1, s2 = st.columns(2)
        s1.metric("Total Stok On Hand (Semua Kategori)", f"{n_stok:,}")
        s2.metric("Jumlah Varian Produk Terdata", f"{int(stock_df['Jumlah Varian Produk'].sum()):,}")

        fig_stock = px.bar(
            stock_df.sort_values("Jumlah Stok (On Hand)", ascending=False),
            x="Kategori Barang", y="Jumlah Stok (On Hand)",
            color="Jumlah Stok (On Hand)", color_continuous_scale=RISK_SCALE[::-1],
            text="Jumlah Stok (On Hand)",
        )
        fig_stock.update_traces(textposition="outside")
        fig_stock.update_layout(**PLOTLY_LAYOUT, showlegend=False, coloraxis_showscale=False,
                                 xaxis_tickangle=-30)
        st.plotly_chart(fig_stock, use_container_width=True)

        render_section_header("Tabel Lengkap: Jumlah Order vs Jumlah Stok per Kategori")
        merged = cat_count.merge(stock_df, on="Kategori Barang", how="outer").fillna(0)
        for col in ["Jumlah Order", "Jumlah Varian Produk"]:
            if col in merged.columns:
                merged[col] = merged[col].astype(int)
        for col in ["Jumlah Stok (On Hand)", "Jumlah Stok (Forecast)"]:
            if col in merged.columns:
                merged[col] = merged[col].round(0).astype(int)
        merged = merged.sort_values("Jumlah Stok (On Hand)", ascending=False)
        st.dataframe(merged, use_container_width=True, height=400)
    else:
        render_section_header("Tabel Lengkap Semua Kategori Barang")
        st.dataframe(cat_count, use_container_width=True, height=360)


def _tab_temporal(df_feat):
    col1, col2 = st.columns(2)
    with col1:
        yr_ch = df_feat.groupby(["first_order_year", "churn_label"]).size().reset_index(name="Count")
        fig_yr2 = px.bar(yr_ch, x="first_order_year", y="Count", color="churn_label", barmode="stack",
                         color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                         title="Komposisi Churn per Tahun Akuisisi",
                         labels={"first_order_year": "Tahun", "Count": "Jumlah", "churn_label": "Status"})
        fig_yr2.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_yr2, use_container_width=True)

    with col2:
        mth_ch = df_feat.groupby("first_order_month")["churn_flag"].agg(["sum", "count"]).reset_index()
        mth_ch.columns = ["Bulan", "Churn", "Total"]
        mth_ch["Churn Rate (%)"] = (mth_ch["Churn"] / mth_ch["Total"] * 100).round(1)
        mth_ch["Bulan Label"] = mth_ch["Bulan"].map(MONTH_LABELS)
        fig_mth = px.line(mth_ch, x="Bulan Label", y="Churn Rate (%)", markers=True,
                          title="Churn Rate per Bulan Akuisisi",
                          color_discrete_sequence=[COLOR_CHURN])
        fig_mth.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_mth, use_container_width=True)

    # Frequency category
    df_freq = df_feat.copy()
    df_freq["freq_cat"] = "Unknown"
    for col_k, lbl in FREQ_DISPLAY_LABELS.items():
        if col_k in df_freq.columns:
            df_freq.loc[df_freq[col_k].isin([True, 1, "True", "1"]), "freq_cat"] = lbl

    fc = df_freq.groupby("freq_cat")["churn_flag"].agg(["sum", "count"]).reset_index()
    fc.columns = ["Kategori", "Churn", "Total"]
    fc["Churn Rate (%)"] = (fc["Churn"] / fc["Total"] * 100).round(1)
    fc["Aktif"] = fc["Total"] - fc["Churn"]

    render_section_header("Churn berdasarkan Frekuensi Pembelian")
    col3, col4 = st.columns(2)
    with col3:
        fig_fc1 = go.Figure()
        fig_fc1.add_bar(x=fc["Kategori"], y=fc["Aktif"], name="Aktif", marker_color=COLOR_ACTIVE)
        fig_fc1.add_bar(x=fc["Kategori"], y=fc["Churn"], name="Churn", marker_color=COLOR_CHURN)
        fig_fc1.update_layout(**PLOTLY_LAYOUT, barmode="stack", title="Komposisi per Frekuensi")
        st.plotly_chart(fig_fc1, use_container_width=True)
    with col4:
        fig_fc2 = px.bar(fc, x="Kategori", y="Churn Rate (%)", color="Churn Rate (%)",
                          color_continuous_scale=RISK_SCALE,
                          text="Churn Rate (%)", title="Churn Rate per Frekuensi")
        fig_fc2.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
        fig_fc2.update_layout(**PLOTLY_LAYOUT, showlegend=False, coloraxis_showscale=False)
        st.plotly_chart(fig_fc2, use_container_width=True)


'''
def _tab_risiko(df_feat):
    col1, col2 = st.columns(2)
    with col1:
        fig_ov = px.box(df_feat, x="churn_label", y="pct_overdue_rentals", color="churn_label",
                         color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                         title="% Rental Terlambat per Status",
                         labels={"pct_overdue_rentals": "% Overdue", "churn_label": "Status"})
        fig_ov.update_layout(**PLOTLY_LAYOUT, showlegend=False)
        st.plotly_chart(fig_ov, use_container_width=True)

    with col2:
        if "pct_problematic_rental_state" in df_feat.columns:
            fig_prob = px.box(df_feat, x="churn_label", y="pct_problematic_rental_state",
                              color="churn_label",
                              color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                              title="% Status Rental Bermasalah",
                              labels={"pct_problematic_rental_state": "% Problematic", "churn_label": "Status"})
            fig_prob.update_layout(**PLOTLY_LAYOUT, showlegend=False)
            st.plotly_chart(fig_prob, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig_conf = px.histogram(df_feat, x="confirmation_rate", color="churn_label",
                                barmode="overlay", nbins=30, opacity=0.75,
                                color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                                title="Distribusi Confirmation Rate",
                                labels={"confirmation_rate": "Confirmation Rate", "churn_label": "Status"})
        fig_conf.update_layout(**PLOTLY_LAYOUT)
        st.plotly_chart(fig_conf, use_container_width=True)

    with col4:
        df_gap = df_feat.dropna(subset=["avg_gap_between_orders_days"])
        if len(df_gap) > 0:
            fig_gap = px.box(df_gap, x="churn_label", y="avg_gap_between_orders_days",
                              color="churn_label",
                              color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                              title="Rata-rata Gap Antar Order (hari)",
                              labels={"avg_gap_between_orders_days": "Gap (hari)", "churn_label": "Status"})
            fig_gap.update_layout(**PLOTLY_LAYOUT, showlegend=False)
            st.plotly_chart(fig_gap, use_container_width=True)
'''