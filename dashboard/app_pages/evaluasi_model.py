"""Halaman Evaluasi Model - performa model pada test set."""
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sklearn.metrics import confusion_matrix, roc_curve, roc_auc_score, precision_recall_curve

from components import render_page_header, render_section_header, render_kpi_card
from config import PLOTLY_LAYOUT, COLOR_CHURN, COLOR_ACTIVE, COLOR_BLUE
from utils import sanitize_columns


def render(model, model_name, model_metrics, feature_cols, requires_scaled, test_raw, test_scaled):
    render_page_header(title=f"Evaluasi Performa Model {model_name}")

    m = model_metrics
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, sub in [
        (c1, "ROC-AUC",   f"{m.get('test_roc_auc', 0):.4f}",        "Area Under Curve"),
        (c2, "Precision", f"{m.get('test_precision_churn', 0):.4f}", "Kelas Churn"),
        (c3, "Recall",    f"{m.get('test_recall_churn', 0):.4f}",    "Kelas Churn"),
        (c4, "F1-Score",  f"{m.get('test_f1_churn', 0):.4f}",        "Kelas Churn"),
    ]:
        with col:
            render_kpi_card("", val, label, sub)

    st.markdown("<br>", unsafe_allow_html=True)

    # Generate test predictions
    test_df = test_scaled.copy() if requires_scaled else test_raw.copy()
    test_san = sanitize_columns(test_df)
    feat_avail = [c for c in feature_cols if c in test_san.columns]
    X_test = test_san[feat_avail]
    if "churn_flag" in X_test.columns:
        X_test = X_test.drop(columns=["churn_flag"])

    y_test_df = sanitize_columns(test_raw.copy())
    y_test = y_test_df["churn_flag"] if "churn_flag" in y_test_df.columns else None

    feat_for_pred = [c for c in feature_cols if c in X_test.columns]

    has_pred = False
    try:
        y_proba = model.predict_proba(X_test[feat_for_pred])[:, 1]
        y_pred = model.predict(X_test[feat_for_pred])
        has_pred = True
    except Exception as e:
        st.error(f"Error prediksi: {e}")

    if has_pred and y_test is not None:
        col_a, col_b = st.columns(2)
        with col_a:
            render_section_header("ROC Curve")
            fpr, tpr, _ = roc_curve(y_test, y_proba)
            auc_val = roc_auc_score(y_test, y_proba)
            fig_roc = go.Figure()
            fig_roc.add_trace(go.Scatter(x=fpr, y=tpr, mode="lines",
                name=f"{model_name} (AUC={auc_val:.4f})",
                line=dict(color=COLOR_BLUE, width=2.5),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)"))
            fig_roc.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines",
                name="Random Guess", line=dict(color="#718096", dash="dash", width=1.5)))
            fig_roc.update_layout(**PLOTLY_LAYOUT, title="ROC Curve - Test Set",
                xaxis_title="False Positive Rate", yaxis_title="True Positive Rate")
            st.plotly_chart(fig_roc, use_container_width=True)

        with col_b:
            render_section_header("Precision-Recall Curve")
            prec, rec, _ = precision_recall_curve(y_test, y_proba)
            fig_pr2 = go.Figure()
            fig_pr2.add_trace(go.Scatter(x=rec, y=prec, mode="lines", name=model_name,
                line=dict(color=COLOR_ACTIVE, width=2.5),
                fill="tozeroy", fillcolor="rgba(16,185,129,0.08)"))
            fig_pr2.update_layout(**PLOTLY_LAYOUT, title="Precision-Recall Curve",
                xaxis_title="Recall", yaxis_title="Precision",
                xaxis_range=[0, 1], yaxis_range=[0, 1.05])
            st.plotly_chart(fig_pr2, use_container_width=True)

        col_c, col_d = st.columns(2)
        with col_c:
            render_section_header("Confusion Matrix")
            cm = confusion_matrix(y_test, y_pred)
            labels = ["Active (0)", "Churn (1)"]
            fig_cm = px.imshow(cm, x=labels, y=labels,
                color_continuous_scale=[[0, "#f0fdf4"], [1, "#10b981"]],
                text_auto=True, aspect="auto", title="Confusion Matrix")
            fig_cm.update_traces(textfont_size=20)
            fig_cm.update_layout(**PLOTLY_LAYOUT, coloraxis_showscale=False,
                xaxis_title="Predicted", yaxis_title="Actual")
            st.plotly_chart(fig_cm, use_container_width=True)

        with col_d:
            render_section_header("Distribusi Probabilitas Prediksi")
            import pandas as pd
            df_prob_plot = pd.DataFrame({"proba": y_proba, "actual": y_test.values})
            df_prob_plot["Status"] = df_prob_plot["actual"].map({0: "Active", 1: "Churn"})
            fig_dist = px.histogram(df_prob_plot, x="proba", color="Status",
                barmode="overlay", nbins=40, opacity=0.75,
                color_discrete_map={"Churn": COLOR_CHURN, "Active": COLOR_ACTIVE},
                title="Distribusi Probabilitas Churn",
                labels={"proba": "Probabilitas Churn", "Status": "Aktual"})
            fig_dist.update_layout(**PLOTLY_LAYOUT)
            st.plotly_chart(fig_dist, use_container_width=True)

    # Feature Importance
    render_section_header("Feature Importance (Top 20)")
    try:
        import pandas as pd
        clf = model.named_steps["classifier"] if hasattr(model, "named_steps") else model
        imp_arr = clf.feature_importances_
        imp_df = pd.DataFrame({"Fitur": feat_for_pred[:len(imp_arr)], "Importance": imp_arr[:len(feat_for_pred)]})
        imp_df = imp_df.sort_values("Importance", ascending=False).head(20)
        fig_imp = px.bar(imp_df, x="Importance", y="Fitur", orientation="h",
            color="Importance",
            color_continuous_scale=["#a7f3d0", "#34d399", "#059669"],
            title="Top 20 Feature Importance")
        layout_imp = PLOTLY_LAYOUT.copy()
        layout_imp["yaxis"] = dict(gridcolor="#e2e8f0", zerolinecolor="#cbd5e1", autorange="reversed")
        layout_imp["coloraxis_showscale"] = False
        layout_imp["height"] = 600
        fig_imp.update_layout(**layout_imp)
        st.plotly_chart(fig_imp, use_container_width=True)
    except Exception as e:
        st.warning(f"Feature importance tidak tersedia: {e}")

    # CV Score info
    if "best_cv_roc_auc" in model_metrics:
        st.info(f"**Cross-Validation ROC-AUC (best):** {model_metrics['best_cv_roc_auc']:.4f}  |  "
                f"**Test ROC-AUC:** {model_metrics['test_roc_auc']:.4f}")
