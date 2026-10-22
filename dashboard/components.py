"""
HTML Component Helpers for Churn Prediction Dashboard
Separates layout and visual templates from core application logic.
"""
import base64
import os
import streamlit as st

from config import LOGO_PATH, NAV_GROUPS, DATA_UPDATED_LABEL


def load_css(css_path="style.css"):
    """Reads and injects external CSS stylesheet into Streamlit."""
    if os.path.exists(css_path):
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def _logo_base64():
    """Encode logo perusahaan sebagai data URI supaya bisa dirender inline di HTML."""
    if not os.path.exists(LOGO_PATH):
        return None
    with open(LOGO_PATH, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def render_page_header(title, subtitle=None):
    """Renders styled page title header, lengkap dengan badge tanggal update data.

    Catatan: HTML dirangkai sebagai satu baris tunggal (tanpa baris kosong di
    tengah) karena Markdown menutup blok HTML mentah begitu menemui baris
    kosong/whitespace-only — kalau tidak, tag setelah baris kosong itu akan
    dicetak sebagai teks literal, bukan dirender sebagai HTML.
    """
    sub_html = f'<p class="page-subtitle">{subtitle}</p>' if subtitle else ""
    badge_html = f'<div class="data-updated-badge">🕒 Data terupdate: {DATA_UPDATED_LABEL}</div>'
    st.markdown(
        f'<div style="padding:24px 0 8px;">'
        f'<h1 class="page-title">{title}</h1>'
        f'{sub_html}'
        f'{badge_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


def render_section_header(title):
    """Renders section header with bottom border accent."""
    st.markdown(f'<div class="section-header">{title}</div>', unsafe_allow_html=True)


def render_kpi_card(icon, value, label, sub="", extra_class=""):
    """Renders a horizontal tile-style KPI card (ikon dalam kotak warna, mirip tile stat Gentelella)."""
    st.markdown(f"""
    <div class="kpi-card {extra_class}">
        <div class="kpi-icon-box"><span class="kpi-icon">{icon}</span></div>
        <div class="kpi-text">
            <div class="kpi-value">{value}</div>
            <div class="kpi-label">{label}</div>
            <div class="kpi-sub">{sub}</div>
        </div>
    </div>""", unsafe_allow_html=True)


def render_prediction_result(pred_lbl, prob, risk_badge_str, is_churn=None, sub_text=None):
    """Renders customer status card.
    is_churn: status aktual (True/False) bila tersedia; jika None, dipakai prob >= 0.5.
    sub_text: teks di bawah persentase (default: 'Probabilitas Churn (skor risiko)')."""
    if is_churn is None:
        is_churn = (prob >= 0.5)
    sub_text = sub_text or "Probabilitas Churn (skor risiko)"
    css_cls = "pred-churn" if is_churn else "pred-active"
    color = "#ef4444" if is_churn else "#29823e"
    emoji = "🔴" if is_churn else "🟢"

    st.markdown(f"""
    <div class="{css_cls}">
        <div class="pred-title" style="color:{color};">{emoji} {pred_lbl}</div>
        <div class="pred-prob" style="color:{color};">{prob:.1%}</div>
        <div class="pred-sub">{sub_text}</div>
        <div style="margin-top:12px;font-size:1rem;font-weight:600;">{risk_badge_str}</div>
    </div>""", unsafe_allow_html=True)


def render_risk_recommendation(prob):
    """Renders actionable recommendations based on churn risk level."""
    if prob >= 0.70:
        st.markdown("""<div class="risk-high">
            <b>🚨 Risiko Tinggi - Tindakan Segera Diperlukan</b><br>
            • Hubungi pelanggan dalam 24-48 jam<br>
            • Tawarkan diskon atau paket loyalitas khusus<br>
            • Assign dedicated account manager<br>
            • Review dan selesaikan outstanding balance segera
        </div>""", unsafe_allow_html=True)
    elif prob >= 0.40:
        st.markdown("""<div class="risk-medium">
            <b>⚠️ Risiko Sedang - Pantau & Engage</b><br>
            • Kirim survei kepuasan pelanggan<br>
            • Tawarkan program referral atau reward points<br>
            • Follow up pada transaksi berikutnya<br>
            • Monitor selama 2 minggu ke depan
        </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""<div class="risk-low">
            <b>✅ Risiko Rendah - Pertahankan Engagement</b><br>
            • Lanjutkan pelayanan standar yang baik<br>
            • Kirim newsletter produk terbaru<br>
            • Pertimbangkan sebagai referral candidate
        </div>""", unsafe_allow_html=True)


def render_winback_recommendation():
    """Rekomendasi untuk pelanggan yang sudah Churn (seluruh kontrak berakhir)."""
    st.markdown("""<div class="risk-medium">
        <b>🔁 Pelanggan Churn - Peluang Win-back</b><br>
        • Hubungi untuk menawarkan kontrak baru / perpanjangan<br>
        • Konfirmasi seluruh unit sudah dikembalikan dan tagihan lunas<br>
        • Tanyakan alasan tidak memperpanjang (harga, kebutuhan, layanan)<br>
        • Masukkan ke daftar penawaran periode berikutnya
    </div>""", unsafe_allow_html=True)


def render_churn_reasons(reasons, risk_level):
    """Renders daftar alasan di balik level risiko churn (Tinggi/Sedang/Rendah).

    `reasons` adalah list tuple (polarity, text) dari utils.generate_churn_reasons,
    dengan polarity salah satu dari 'negative', 'positive', 'neutral'.
    """
    if not reasons:
        st.info("Alasan detail tidak tersedia — data pendukung untuk pelanggan ini kurang lengkap.")
        return

    icon_map = {"negative": "🔴", "positive": "🟢", "neutral": "⚪"}
    items_html = "".join(
        f'<li class="reason-item reason-{polarity}"><span>{icon_map.get(polarity, "⚪")}</span> {text}</li>'
        for polarity, text in reasons
    )
    st.markdown(f"""
    <div class="reason-box">
        <div class="reason-box-title">Mengapa risiko churn-nya <b>{risk_level}</b>?</div>
        <ul class="reason-list">{items_html}</ul>
    </div>""", unsafe_allow_html=True)


def render_sidebar_header():
    """Renders company logo and title in sidebar."""
    logo_b64 = _logo_base64()
    logo_html = (
        f'<img class="sidebar-logo" src="data:image/png;base64,{logo_b64}">'
        if logo_b64 else '<div style="font-size:2.8rem;">🔄</div>'
    )
    st.markdown(f"""
    <div class="sidebar-header">
        {logo_html}
        <div class="sidebar-title">PESONNA OPTIMA JASA</div>
        <div class="sidebar-subtitle">Solution &amp; Trust</div>
    </div>""", unsafe_allow_html=True)


def render_sidebar_nav():
    """Renders navigasi sidebar sebagai list yang dikelompokkan per kategori.

    Menyimpan halaman aktif di st.session_state['current_page'] dan
    mengembalikan nilainya supaya app.py bisa melakukan routing.
    """
    if "current_page" not in st.session_state:
        first_group = next(iter(NAV_GROUPS.values()))
        st.session_state.current_page = first_group[0]

    for group_label, pages in NAV_GROUPS.items():
        # st.sidebar.markdown(f'<div class="nav-group-label">{group_label}</div>', unsafe_allow_html=True)
        for page_name in pages:
            is_active = (st.session_state.current_page == page_name)
            if st.sidebar.button(
                page_name,
                key=f"nav_btn_{page_name}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.current_page = page_name
                st.rerun()

    return st.session_state.current_page


def render_footer():
    """Renders footer at the bottom of the dashboard."""
    st.markdown("""
    <div class="footer-container">
        <hr class="footer-hr">
        <span class="footer-accent">PT Pesonna Optima Jasa</span> &nbsp;|&nbsp;
        Dashboard Prediksi Churn Pelanggan Rental &nbsp;|&nbsp;
        Solution &amp; Trust
    </div>""", unsafe_allow_html=True)

def render_crm_info(cust_row):
    """Menampilkan Opportunity & Notes dari CRM dengan tampilan terpisah:
    bagian Opportunity di atas dan bagian Notes di bawah."""
    import html
    n = int(cust_row.get("crm_n_opportunity", 0) or 0)
    if n == 0:
        st.info("ℹ️ Belum ada data opportunity & notes (Rental) di CRM untuk pelanggan ini.")
        return

    raw_opps = str(cust_row.get("crm_opportunity", "") or "")
    raw_notes = str(cust_row.get("crm_notes", "") or "")

    opps = [o.strip() for o in raw_opps.split(" || ") if o.strip()]
    notes_list = [n.strip() for n in raw_notes.split(" || ")] if raw_notes else []

    # 1. Bagian Atas: Opportunity
    st.markdown("##### 🎯 Opportunity")
    if opps:
        for i, opp in enumerate(opps, 1):
            num_badge = f"<b>{i}.</b> " if len(opps) > 1 else ""
            st.markdown(
                f'<div class="crm-item crm-opp-item">'
                f'{num_badge}{html.escape(opp)}'
                f'</div>',
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            '<div class="crm-item crm-opp-item" style="color:#64748b;font-style:italic;">'
            'Tidak ada data opportunity tercatat.'
            '</div>',
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

    # 2. Bagian Bawah: Notes
    st.markdown("##### 📝 Notes")
    valid_notes = [nt for nt in notes_list if nt and str(nt).strip() and str(nt).strip().lower() != "nan"]
    if not valid_notes:
        st.markdown(
            '<div class="crm-item crm-notes-item" style="color:#64748b;font-style:italic;">'
            'Tidak ada catatan (notes) di CRM untuk pelanggan ini.'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        for i, note in enumerate(valid_notes, 1):
            num_badge = f"<b>{i}.</b> " if len(valid_notes) > 1 else ""
            note_content = html.escape(note).replace("\n", "<br>")
            st.markdown(
                f'<div class="crm-item crm-notes-item">'
                f'{num_badge}{note_content}'
                f'</div>',
                unsafe_allow_html=True,
            )
