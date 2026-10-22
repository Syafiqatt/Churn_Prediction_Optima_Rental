"""Halaman Data Explorer - filter dan tabel data pelanggan."""
import streamlit as st

from components import render_page_header
from utils import df_download_button, format_date_id


def render(df_feat):
    render_page_header(title="Data Explorer")

    cf1, cf2, cf3 = st.columns(3)
    with cf1:
        status_flt = st.multiselect("Filter Status", ["Churn", "Active"], default=["Churn", "Active"])
    with cf2:
        min_ord = st.number_input("Min Total Order", 0, value=0)
    with cf3:
        sort_col = st.selectbox("Urutkan Berdasarkan",
            ["Customer", "risk_prob", "last_end_date", "total_invoiced", "total_orders", "order_span_days", "payment_ratio_imputed", "pct_overdue_rentals"])

    dfe = df_feat[df_feat["churn_label"].isin(status_flt)]
    
    # Urutkan secara Ascending jika berdasarkan nama Customer, sisanya Descending
    is_asc = sort_col in ("Customer", "last_end_date")
    dfe = dfe[dfe["total_orders"] >= min_ord].sort_values(sort_col, ascending=is_asc)

    show_cols = [c for c in [
        "Customer", "churn_label", "last_end_date", "risk_prob", "total_orders", "total_invoiced", "total_paid",
        "payment_ratio_imputed", "outstanding_balance", "order_span_days",
        "avg_lifetime_days", "pct_overdue_rentals", "avg_project_value", "first_order_year",
        "crm_n_opportunity", "crm_opportunity", "crm_notes",
    ] if c in dfe.columns]

    st.metric("Jumlah Pelanggan", f"{len(dfe):,}")
    st.caption("Status: **Churn** = End Date terakhir sudah lewat (risiko 100%, status pasti); "
               "**Active** = masih ada kontrak berjalan (risiko = skor model).")

    rename_map = {
        "Customer": "Pelanggan", "churn_label": "Status", "total_orders": "Total Order",
        "last_end_date": "Kontrak Berakhir", "risk_prob": "Risiko Churn (%)",
        "total_invoiced": "Total Invoiced", "total_paid": "Total Paid",
        "payment_ratio_imputed": "Pay Ratio (%)", "outstanding_balance": "Outstanding",
        "order_span_days": "Rentang Order (hari)", "avg_lifetime_days": "Avg Lifetime (hari)",
        "pct_overdue_rentals": "% Overdue", "avg_project_value": "Avg Project Val",
        "first_order_year": "Tahun Akuisisi",
        "crm_n_opportunity": "Jumlah Opportunity", "crm_opportunity": "Opportunity (CRM)", "crm_notes": "Notes (CRM)",
    }
    dfe_show = dfe[show_cols].copy()
    dfe_show["last_end_date"] = dfe_show["last_end_date"].apply(format_date_id)
    dfe_show["risk_prob"] = (dfe_show["risk_prob"] * 100).round(1)
    dfe_show = dfe_show.rename(columns=rename_map)
    dfe_show.index = range(1, len(dfe_show) + 1)

    def style_status(val):
        if val == "Churn":
            return "color:#ef4444;font-weight:bold"
        return "color:#29823e;font-weight:bold"

    st.dataframe(dfe_show.style.map(style_status, subset=["Status"]),
                 use_container_width=True, height=480)

    df_download_button(st, dfe_show, "⬇️ Unduh Data Terfilter (CSV)", "data_explorer_filtered.csv")
