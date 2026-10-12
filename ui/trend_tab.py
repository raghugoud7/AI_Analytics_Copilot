import pandas as pd
import plotly.express as px
import streamlit as st

CHART_COLORS = {
    "volume": "#2563EB",
    "kpi": "#10B981",
    "daily": "#8B5CF6",
    "daily_kpi": "#F59E0B",
}


def render_trend_tab(analysis: dict):
    st.subheader("📈 Trend Analysis")

    if not analysis.get("success", False):
        st.warning(analysis.get("error", "No trend analysis available."))
        return

    st.metric("Target KPI", analysis.get("kpi_column", "N/A"))

    for date_col, trend_data in analysis.get("trends", {}).items():
        st.divider()
        st.markdown(f"## {date_col}")

        monthly_df = pd.DataFrame(trend_data.get("monthly_trend", []))
        daily_df = pd.DataFrame(trend_data.get("daily_trend", []))

        c1, c2 = st.columns(2)
        c1.metric("Monthly Points", len(monthly_df))
        c2.metric("Daily Points", len(daily_df))

        st.markdown("### 📅 Monthly Trends")

        if monthly_df.empty:
            st.info("No monthly trend data available.")
        else:
            monthly_df["period"] = pd.to_datetime(monthly_df["period"])

            volume_fig = px.line(
                monthly_df,
                x="period",
                y="record_count",
                markers=True,
                title=f"{date_col} Monthly Volume Trend",
                color_discrete_sequence=[CHART_COLORS["volume"]],
            )

            volume_fig.update_layout(
                height=450,
                xaxis_title="Period",
                yaxis_title="Record Count",
            )

            st.plotly_chart(volume_fig, width="stretch")

            if "avg_kpi" in monthly_df.columns:
                kpi_fig = px.line(
                    monthly_df,
                    x="period",
                    y="avg_kpi",
                    markers=True,
                    title=f"{date_col} Monthly KPI Trend",
                    color_discrete_sequence=[CHART_COLORS["kpi"]],
                )

                kpi_fig.update_layout(
                    height=450,
                    xaxis_title="Period",
                    yaxis_title="Average KPI",
                )

                st.plotly_chart(kpi_fig, width="stretch")

        if not daily_df.empty:
            daily_df["period"] = pd.to_datetime(daily_df["period"])

            with st.expander("📆 Daily Trend Details"):
                volume_fig = px.line(
                    daily_df,
                    x="period",
                    y="record_count",
                    title=f"{date_col} Daily Volume Trend",
                    color_discrete_sequence=[CHART_COLORS["daily"]],
                )

                volume_fig.update_layout(
                    height=450,
                    xaxis_title="Date",
                    yaxis_title="Record Count",
                )

                st.plotly_chart(volume_fig, width="stretch")

                if "avg_kpi" in daily_df.columns:
                    kpi_fig = px.line(
                        daily_df,
                        x="period",
                        y="avg_kpi",
                        title=f"{date_col} Daily KPI Trend",
                        color_discrete_sequence=[CHART_COLORS["daily_kpi"]],
                    )

                    kpi_fig.update_layout(
                        height=450,
                        xaxis_title="Date",
                        yaxis_title="Average KPI",
                    )

                    st.plotly_chart(kpi_fig, width="stretch")

                st.dataframe(
                    daily_df.tail(30),
                    width="stretch",
                    hide_index=True,
                )
        else:
            st.info("No daily trend data available.")