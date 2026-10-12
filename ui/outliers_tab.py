import pandas as pd
import plotly.express as px
import streamlit as st

from ui.chart_utils import apply_chart_style


def render_outlier_tab(outlier_analysis: dict):

    if not outlier_analysis.get("success", False):
        st.error(
            outlier_analysis.get(
                "error",
                "Outlier analysis failed.",
            )
        )
        return

    st.subheader("🚨 Outlier Detection")

    outliers = outlier_analysis.get(
        "all_outliers",
        {},
    )

    if not outliers:
        st.info("No outliers detected.")
        return

    anomaly_df = (
        pd.DataFrame.from_dict(
            outliers,
            orient="index",
        )
        .reset_index()
        .rename(columns={"index": "column"})
    )

    # =====================================
    # Summary Metrics
    # =====================================

    c1, c2, c3, c4 = st.columns(4)

    c1.metric(
        "Numeric Columns",
        outlier_analysis.get(
            "numeric_columns",
            0,
        ),
    )

    c2.metric(
        "Outlier Columns",
        outlier_analysis.get(
            "outlier_columns",
            0,
        ),
    )

    c3.metric(
        "Max Outliers",
        int(anomaly_df["outlier_count"].max()),
    )

    c4.metric(
        "Highest %",
        f"{anomaly_df['outlier_percentage'].max():.2f}%",
    )

    # =====================================
    # Outlier Count Chart
    # =====================================

    st.markdown(
        "### 🚨 Columns With Most Outliers"
    )

    top_outliers = anomaly_df.sort_values(
        "outlier_count",
        ascending=False,
    ).head(15)

    fig = px.bar(
        top_outliers,
        x="column",
        y="outlier_count",
        color="outlier_percentage",
        text="outlier_count",
        color_continuous_scale="Reds",
        title="Outlier Count by Column",
    )

    fig = apply_chart_style(fig)

    fig.update_layout(
        xaxis_title="Column",
        yaxis_title="Outlier Count",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # =====================================
    # Outlier Percentage Chart
    # =====================================

    st.markdown(
        "### 📊 Outlier Percentage"
    )

    fig = px.bar(
        top_outliers.sort_values(
            "outlier_percentage",
            ascending=False,
        ),
        x="column",
        y="outlier_percentage",
        color="outlier_percentage",
        text="outlier_percentage",
        color_continuous_scale="Oranges",
        title="Outlier Percentage by Column",
    )

    fig = apply_chart_style(fig)

    fig.update_layout(
        xaxis_title="Column",
        yaxis_title="Outlier %",
    )

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # =====================================
    # IQR Boundaries
    # =====================================

    st.markdown(
        "### 📏 Outlier Detection Boundaries"
    )

    boundary_df = top_outliers[
        [
            "column",
            "lower_bound",
            "upper_bound",
        ]
    ]

    fig = px.scatter(
        boundary_df,
        x="lower_bound",
        y="upper_bound",
        text="column",
        color="upper_bound",
        title="IQR Boundaries",
    )

    fig.update_traces(
        textposition="top center",
    )

    fig = apply_chart_style(fig)

    st.plotly_chart(
        fig,
        width="stretch",
    )

    # =====================================
    # Download Section
    # =====================================

    st.markdown(
        "### ⬇️ Download Results"
    )

    st.download_button(
        "Download Outlier Analysis CSV",
        data=anomaly_df.to_csv(index=False),
        file_name="outlier_analysis.csv",
        mime="text/csv",
    )

    # =====================================
    # Detailed Results
    # =====================================

    with st.expander(
        "📋 Detailed Outlier Results"
    ):
        st.dataframe(
            anomaly_df.sort_values(
                "outlier_percentage",
                ascending=False,
            ),
            width="stretch",
            hide_index=True,
        )