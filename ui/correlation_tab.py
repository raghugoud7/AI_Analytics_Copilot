import pandas as pd
import plotly.express as px
import streamlit as st




def render_correlation_tab(correlation_analysis: dict):

    if not correlation_analysis.get("success", False):
        st.error(
            correlation_analysis.get(
                "error",
                "Correlation analysis failed.",
            )
        )
        return
    
    positive_df = pd.DataFrame()
    negative_df = pd.DataFrame()
    st.subheader("🔗 Correlation Analysis")

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Correlations",
        correlation_analysis.get(
            "correlation_count",
            0,
        ),
    )

    c2.metric(
        "Top Positive",
        len(
            correlation_analysis.get(
                "top_positive",
                [],
            )
        ),
    )

    c3.metric(
        "Top Negative",
        len(
            correlation_analysis.get(
                "top_negative",
                [],
            )
        ),
    )

    # =====================================
    # Heatmap
    # =====================================

    corr_matrix = correlation_analysis.get(
        "correlation_matrix",
        {},
    )

    if corr_matrix:

        st.markdown(
            "### 🔥 Correlation Heatmap"
        )

        corr_df = pd.DataFrame(
            corr_matrix
        )

        fig = px.imshow(
            corr_df,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            zmin=-1,
            zmax=1,
            aspect="auto",
            title="Correlation Matrix",
        )

        fig.update_layout(
            height=700,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )
        
        st.download_button(
            "⬇️ Download Correlation Matrix",
            data=corr_df.to_csv(index=True),
            file_name="correlation_matrix.csv",
            mime="text/csv",
        )

    # =====================================
    # Strongest Correlations
    # =====================================

    top_corr = correlation_analysis.get(
        "top_correlations",
        [],
    )

    if top_corr:

        st.markdown(
            "### 📈 Strongest Relationships"
        )

        top_df = pd.DataFrame(top_corr)

        top_df["relationship"] = (
            top_df["column_1"]
            + " ↔ "
            + top_df["column_2"]
        )

        fig = px.bar(
            top_df.head(15),
            x="correlation",
            y="relationship",
            orientation="h",
            color="correlation",
            color_continuous_scale="Viridis",
            title="Top Correlations",
        )

        fig.update_layout(
            height=500,
            yaxis={"categoryorder": "total ascending"},
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

        with st.expander(
            "View Correlation Details"
        ):
            st.dataframe(
                top_df,
                width="stretch",
                hide_index=True,
            )
            
    if top_corr:

        top_df = pd.DataFrame(top_corr)

        with st.expander(
            "View Correlation Details"
        ):
            st.dataframe(
                top_df,
                width="stretch",
                hide_index=True,
            )

            st.download_button(
                "⬇️ Download Correlations CSV",
                data=top_df.to_csv(index=False),
                file_name="correlation_analysis.csv",
                mime="text/csv",
            )

    # =====================================
    # Positive Correlations
    # =====================================

    positive = correlation_analysis.get(
        "top_positive",
        [],
    )

    if positive:

        st.markdown(
            "### ✅ Top Positive Correlations"
        )

        positive_df = pd.DataFrame(
            positive
        )

        positive_df["relationship"] = (
            positive_df["column_1"]
            + " ↔ "
            + positive_df["column_2"]
        )

        positive_df = positive_df.sort_values(
            "correlation",
            ascending=False,
        )

        fig = px.bar(
            positive_df,
            x="correlation",
            y="relationship",
            orientation="h",
            color="correlation",
            text="correlation",
            color_continuous_scale="Greens",
        )

        fig.update_layout(
            height=500,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # =====================================
    # Negative Correlations
    # =====================================

    negative = correlation_analysis.get(
        "top_negative",
        [],
    )

    if negative:

        st.markdown(
            "### ⚠️ Top Negative Correlations"
        )

        negative_df = pd.DataFrame(
            negative
        )

        negative_df["relationship"] = (
            negative_df["column_1"]
            + " ↔ "
            + negative_df["column_2"]
        )

        negative_df = negative_df.sort_values(
            "correlation",
        )

        fig = px.bar(
            negative_df,
            x="correlation",
            y="relationship",
            orientation="h",
            color="correlation",
            text="correlation",
            color_continuous_scale="Reds_r",
        )

        fig.update_layout(
            height=500,
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    c1, c2 = st.columns(2)

    with c1:
        if not positive_df.empty:
            st.download_button(
                "⬇️ Positive Correlations",
                data=positive_df.to_csv(index=False),
                file_name="positive_correlations.csv",
                mime="text/csv",
            )

    with c2:
        if not negative_df.empty:
            st.download_button(
                "⬇️ Negative Correlations",
                data=negative_df.to_csv(index=False),
                file_name="negative_correlations.csv",
                mime="text/csv",
            )
        
    # =====================================
    # Correlation Summary
    # =====================================

    if top_corr:

        strong = [
            c
            for c in top_corr
            if abs(c["correlation"]) >= 0.7
        ]

        moderate = [
            c
            for c in top_corr
            if 0.3 <= abs(c["correlation"]) < 0.7
        ]

        weak = [
            c
            for c in top_corr
            if abs(c["correlation"]) < 0.3
        ]

        st.markdown(
            "### 📋 Correlation Summary"
        )

        c1, c2, c3 = st.columns(3)

        c1.metric(
            "Strong",
            len(strong),
        )

        c2.metric(
            "Moderate",
            len(moderate),
        )

        c3.metric(
            "Weak",
            len(weak),
        )
        
