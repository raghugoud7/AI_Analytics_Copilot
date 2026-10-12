import pandas as pd
import plotly.express as px
import streamlit as st

CHART_COLORS = {
    "segment": "#2563EB",
    "difference": "#10B981",
    "significant": "#8B5CF6",
    "distribution": px.colors.qualitative.Set3,
}


def render_segment_tab(analysis: dict):
    st.subheader("📊 Segment Analysis")

    # analysis["segments"] is already being passed from app.py
    if not analysis.get("success", False):
        st.warning(analysis.get("error", "No segment analysis available."))
        return

    st.metric("Target KPI", analysis.get("target_kpi", "N/A"))

    for dim, details in analysis.get("segments", {}).items():
        st.divider()
        st.markdown(f"## {dim}")

        c1, c2, c3 = st.columns(3)
        c1.metric("Cardinality", details.get("cardinality", 0))
        c2.metric("Overall KPI", details.get("overall_kpi", 0))
        c3.metric("Segments", len(details.get("top_segments", [])))

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### 🏆 Best Segment")

            if best_segment := details.get("best_segment"):
                st.dataframe(
                    pd.DataFrame([best_segment]),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No best segment available.")

        with col2:
            st.markdown("### 📉 Worst Segment")

            if worst_segment := details.get("worst_segment"):
                st.dataframe(
                    pd.DataFrame([worst_segment]),
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No worst segment available.")

        segment_df = pd.DataFrame(details.get("top_segments", []))

        if segment_df.empty:
            st.info("No segment data available.")
            continue

        if "avg_kpi" in segment_df.columns:
            st.markdown("### 📈 Segment Comparison")

            fig = px.bar(
                segment_df.sort_values("avg_kpi", ascending=False),
                x="segment",
                y="avg_kpi",
                color="avg_kpi",
                text="avg_kpi",
                title=f"{dim} Performance",
                color_continuous_scale="Blues",
            )

            fig.update_layout(
                height=450,
                xaxis_title=dim,
                yaxis_title="Average KPI",
            )

            st.plotly_chart(fig, width="stretch")

        if "difference_from_average" in segment_df.columns:
            st.markdown("### 🎯 KPI Difference From Average")

            fig = px.bar(
                segment_df.sort_values(
                    "difference_from_average",
                    ascending=False,
                ),
                x="segment",
                y="difference_from_average",
                color="difference_from_average",
                text="difference_from_average",
                title="Difference from Overall KPI",
                color_continuous_scale="RdYlGn",
            )

            fig.update_layout(
                height=450,
                xaxis_title=dim,
                yaxis_title="Difference",
            )

            st.plotly_chart(fig, width="stretch")

        if "segment_percentage" in segment_df.columns:
            st.markdown("### 🥧 Segment Distribution")

            fig = px.pie(
                segment_df,
                names="segment",
                values="segment_percentage",
                hole=0.45,
                title="Segment Distribution (%)",
                color_discrete_sequence=CHART_COLORS["distribution"],
            )

            fig.update_layout(height=500)
            st.plotly_chart(fig, width="stretch")

        if "significant" in segment_df.columns:
            significant_df = segment_df[segment_df["significant"]]

            if not significant_df.empty:
                st.markdown("### ✅ Significant Segments")

                plot_df = significant_df.copy()
                plot_df["significance_rank"] = plot_df["significance"].map(
                    {
                        "Highly Significant": 1,
                        "Significant": 2,
                        "Not Significant": 3,
                    }
                )

                plot_df = plot_df.sort_values(
                    ["significance_rank", "avg_kpi"],
                    ascending=[True, False],
                )

                fig = px.bar(
                    plot_df,
                    x="segment",
                    y="avg_kpi",
                    color="significance",
                    text="avg_kpi",
                    hover_data=[
                        "record_count",
                        "segment_percentage",
                        "difference_from_average",
                        "p_value",
                    ],
                    title="Statistically Significant Segments",
                    color_discrete_map={
                        "Highly Significant": "#10B981",
                        "Significant": "#2563EB",
                        "Not Significant": "#EF4444",
                    },
                )

                fig.update_layout(
                    height=450,
                    xaxis_title="Segment",
                    yaxis_title="Average KPI",
                    showlegend=True,
                    template="plotly_white",
                )

                fig.update_traces(textposition="outside")

                st.plotly_chart(fig, width="stretch")

                st.dataframe(
                    significant_df,
                    width="stretch",
                    hide_index=True,
                )