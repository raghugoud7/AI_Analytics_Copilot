import pandas as pd
import plotly.express as px
import streamlit as st


STRENGTH_COLORS = {
    "Very Strong": "#006400",
    "Strong": "#2E8B57",
    "Moderate": "#FFA500",
    "Weak": "#FF6347",
    "Very Weak": "#DC143C",
}


def get_strength(correlation: float) -> str:
    corr = abs(float(correlation))

    if corr >= 0.80:
        return "Very Strong"
    if corr >= 0.60:
        return "Strong"
    if corr >= 0.40:
        return "Moderate"
    if corr >= 0.20:
        return "Weak"

    return "Very Weak"


def safe_dict(value):
    return value if isinstance(value, dict) else {}


def format_chart(fig, title: str):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=500,
        font={"size": 14},
        title_font={"size": 18},
        margin=dict(l=20, r=20, t=60, b=20),
        legend_title_text="",
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(0,0,0,0.08)")

    return fig


def render_drivers_tab(driver_analysis: dict):

    if not driver_analysis.get("success", False):
        st.error(
            driver_analysis.get(
                "error",
                "Driver analysis failed.",
            )
        )
        return

    st.subheader("🎯 Driver Analysis")

    target = driver_analysis.get("target", "N/A")

    strongest_positive = safe_dict(
        driver_analysis.get("strongest_positive")
    )

    strongest_negative = safe_dict(
        driver_analysis.get("strongest_negative")
    )

    positive_df = pd.DataFrame(
        driver_analysis.get(
            "top_positive_drivers",
            [],
        )
    )

    negative_df = pd.DataFrame(
        driver_analysis.get(
            "top_negative_drivers",
            [],
        )
    )

    recommendations = driver_analysis.get(
        "recommendations",
        [],
    )

    for df in [positive_df, negative_df]:
        if (
            not df.empty
            and "correlation" in df.columns
            and "strength" not in df.columns
        ):
            df["strength"] = df["correlation"].apply(
                get_strength
            )

    # =====================================
    # Summary
    # =====================================

    c1, c2, c3 = st.columns(3)

    c1.metric(
        "Target KPI",
        target,
    )

    c2.metric(
        "Strongest Positive",
        strongest_positive.get(
            "driver",
            "N/A",
        ),
        (
            f"+{strongest_positive.get('correlation')}"
            if strongest_positive.get(
                "correlation"
            )
            is not None
            else None
        ),
    )

    c3.metric(
        "Strongest Negative",
        strongest_negative.get(
            "driver",
            "N/A",
        ),
        strongest_negative.get(
            "correlation",
        ),
    )

    # =====================================
    # Positive Drivers
    # =====================================

    # if not positive_df.empty:
    if (not positive_df.empty
    and {"driver", "correlation",}.issubset(positive_df.columns)
    ):
        st.markdown("### ✅ Top Positive Drivers")
        
        positive_df = positive_df.sort_values(
            "correlation",
            ascending=True,
        )

        fig = px.bar(
            positive_df,
            x="correlation",
            y="driver",
            orientation="h",
            color="strength",
            text="correlation",
            color_discrete_map=STRENGTH_COLORS,
        )

        fig.update_traces(
            texttemplate="%{text:.3f}",
            textposition="outside",
        )

        fig = format_chart(
            fig,
            f"Top Positive Drivers of {target}",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # =====================================
    # Negative Drivers
    # =====================================

    if not negative_df.empty:

        st.markdown("### ⚠️ Top Negative Drivers")

        negative_df = negative_df.sort_values(
            "correlation"
        )

        fig = px.bar(
            negative_df,
            x="correlation",
            y="driver",
            orientation="h",
            color="strength",
            text="correlation",
            color_discrete_map=STRENGTH_COLORS,
        )

        fig.update_traces(
            texttemplate="%{text:.3f}",
            textposition="outside",
        )

        fig = format_chart(
            fig,
            f"Top Negative Drivers of {target}",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # =====================================
    # Correlation Distribution
    # =====================================

    all_drivers = pd.concat(
        [positive_df, negative_df],
        ignore_index=True,
    )

    # if not all_drivers.empty:
    if (
    not all_drivers.empty
    and {
        "correlation",
        "strength",
    }.issubset(
        all_drivers.columns
    )
):

        st.markdown(
            "### 📊 Correlation Distribution"
        )

        fig = px.histogram(
            all_drivers,
           x="correlation",
            color="strength",
            nbins=15,
            color_discrete_map=STRENGTH_COLORS,
        )

        fig = format_chart(
            fig,
            "Driver Correlation Distribution",
        )

        st.plotly_chart(
            fig,
            width="stretch",
        )

    # =====================================
    # Recommendations
    # =====================================

    if recommendations:

        st.markdown(
            "### 🚀 Recommendations"
        )

        for recommendation in recommendations:
            st.success(recommendation)

    # =====================================
    # Download
    # =====================================

    if not all_drivers.empty:

        st.markdown(
            "### ⬇️ Download Results"
        )

        st.download_button(
            "Download Driver Analysis CSV",
            data=all_drivers.to_csv(
                index=False,
            ),
            file_name="driver_analysis.csv",
            mime="text/csv",
        )

    # =====================================
    # Detailed Tables
    # =====================================

    col1, col2 = st.columns(2)

    with col1:

        if not positive_df.empty:

            with st.expander(
                "✅ Positive Driver Details"
            ):

                st.dataframe(
                    positive_df,
                    width="stretch",
                    hide_index=True,
                )

    with col2:

        if not negative_df.empty:

            with st.expander(
                "⚠️ Negative Driver Details"
            ):

                st.dataframe(
                    negative_df,
                    width="stretch",
                    hide_index=True,
                )

    # =====================================
    # Executive Insights
    # =====================================

    st.markdown(
        "### 📌 Executive Insights"
    )

    if strongest_positive:

        st.success(
            f"✅ '{strongest_positive.get('driver')}' "
            f"is the strongest positive driver of "
            f"'{target}' with correlation "
            f"{strongest_positive.get('correlation')}."
        )

    if strongest_negative:

        st.warning(
            f"⚠️ '{strongest_negative.get('driver')}' "
            f"is the strongest negative driver of "
            f"'{target}' with correlation "
            f"{strongest_negative.get('correlation')}."
        )