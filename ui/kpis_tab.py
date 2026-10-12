import pandas as pd
import plotly.express as px
import streamlit as st


def render_kpis_tab(kpi_analysis: dict) -> None:
    st.subheader("📊 KPI Analysis")

    if not isinstance(kpi_analysis, dict):
        st.error("Invalid KPI analysis response.")
        return

    if not kpi_analysis.get("success", False):
        st.error(kpi_analysis.get("error", "KPI analysis failed."))
        return

    kpis = kpi_analysis.get("kpis", [])
    if not kpis:
        st.info("No KPI columns were identified.")
        return

    kpi_df = pd.DataFrame(kpis)

    required_columns = {
        "kpi",
        "record_count",
        "null_percentage",
        "average",
        "median",
        "minimum",
        "maximum",
        "std_dev",
        "p25",
        "p75",
    }

    missing_columns = required_columns.difference(kpi_df.columns)
    if missing_columns:
        st.error(f"Missing KPI fields: {', '.join(sorted(missing_columns))}")
        st.write("Available fields:", kpi_df.columns.tolist())
        return

    numeric_cols = [
        "record_count",
        "null_percentage",
        "average",
        "median",
        "minimum",
        "maximum",
        "std_dev",
        "p25",
        "p75",
    ]

    for col in numeric_cols:
        if col in kpi_df.columns:
            kpi_df[col] = pd.to_numeric(kpi_df[col], errors="coerce")

    top_n = min(4, len(kpi_df))
    top_kpis = kpi_df.sort_values("average", ascending=False).head(top_n)

    for column, (_, row) in zip(st.columns(top_n), top_kpis.iterrows()):
        column.metric(
            label=row["kpi"],
            value=f"{row['average']:,.2f}" if pd.notna(row["average"]) else "N/A",
            delta=(
                f"Median: {row['median']:,.2f}"
                if pd.notna(row["median"])
                else "Median: N/A"
            ),
        )

    with st.expander("🎛️ KPI Filters", expanded=False):
        f1, f2, f3 = st.columns(3)

        selected_kpis = f1.multiselect(
            "Select KPIs",
            options=kpi_df["kpi"].dropna().tolist(),
            default=kpi_df["kpi"].dropna().tolist(),
            key="kpi_tab_selected_kpis",
        )

        metric = f2.selectbox(
            "Comparison Metric",
            ["average", "median", "minimum", "maximum", "std_dev"],
            format_func=lambda x: x.replace("_", " ").title(),
            key="kpi_tab_metric",
        )

        sort_order = f3.selectbox(
            "Sort Order",
            ["Highest first", "Lowest first"],
            key="kpi_tab_sort_order",
        )

    kpi_filter_mask = kpi_df["kpi"].isin(selected_kpis)
    filtered_df: pd.DataFrame = kpi_df.loc[kpi_filter_mask].copy()  # type: ignore

    if filtered_df.empty:
        st.warning("Select at least one KPI.")
        return

    ascending = sort_order == "Lowest first"

    if metric not in filtered_df.columns:
        st.error(f"Metric '{metric}' not found.")
        return

    filtered_df = filtered_df.sort_values(by=metric, ascending=ascending)

    st.markdown("### 📈 KPI Comparison")

    chart_df = filtered_df.head(20)

    fig = px.bar(
        chart_df,
        x=metric,
        y="kpi",
        orientation="h",
        color=metric,
        text=metric,
        color_continuous_scale="Blues",
        title=f"KPI {metric.replace('_', ' ').title()} Comparison",
    )

    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        height=max(450, len(chart_df) * 38),
        xaxis_title=metric.replace("_", " ").title(),
        yaxis_title="KPI",
        yaxis={"categoryorder": "total ascending"},
    )

    st.plotly_chart(fig, width="stretch")

    st.markdown("### 📏 KPI Range and Quartiles")

    range_df = filtered_df.head(15)

    scatter_cols = {"average", "record_count", "null_percentage"}

    if scatter_cols.issubset(range_df.columns):
        hover_data = {
            col: ":.2f"
            for col in [
                "median",
                "minimum",
                "maximum",
                "std_dev",
                "p25",
                "p75",
            ]
            if col in range_df.columns
        }

        hover_data.update(
            {
                "record_count": ":.0f",
                "null_percentage": ":.2f",
            }
        )

        fig = px.scatter(
            range_df,
            x="average",
            y="kpi",
            size="record_count",
            color="null_percentage",
            hover_data=hover_data,
            color_continuous_scale="RdYlGn_r",
            title="KPI Average, Volume, and Missing-Value Percentage",
        )

        fig.update_layout(
            height=max(450, len(range_df) * 38),
            xaxis_title="Average",
            yaxis_title="KPI",
        )

        st.plotly_chart(fig, width="stretch")

    st.markdown("### ✅ KPI Data Completeness")

    completeness_df = filtered_df[["kpi", "null_percentage"]].copy()
    completeness_df["completeness_percentage"] = (
        100 - completeness_df["null_percentage"]
    )

    fig = px.bar(
        completeness_df.sort_values(by=["completeness_percentage"]),
        x="completeness_percentage",
        y="kpi",
        orientation="h",
        color="completeness_percentage",
        text="completeness_percentage",
        color_continuous_scale="RdYlGn",
        range_x=[0, 100],
        title="KPI Completeness Percentage",
    )

    fig.update_traces(texttemplate="%{text:.2f}%", textposition="outside")
    fig.update_layout(
        height=max(450, len(completeness_df) * 38),
        xaxis_title="Completeness %",
        yaxis_title="KPI",
    )

    st.plotly_chart(fig, width="stretch")

    with st.expander("📋 View KPI Details"):
        display_columns = [
            col
            for col in [
                "kpi",
                "record_count",
                "null_percentage",
                "average",
                "median",
                "minimum",
                "maximum",
                "std_dev",
                "p25",
                "p75",
            ]
            if col in filtered_df.columns
        ]

        st.dataframe(
            filtered_df[display_columns],
            width="stretch",
            hide_index=True,
            column_config={
                "kpi": st.column_config.TextColumn("KPI"),
                "record_count": st.column_config.NumberColumn("Records", format="%d"),
                "null_percentage": st.column_config.NumberColumn(
                    "Missing %", format="%.2f%%"
                ),
                "average": st.column_config.NumberColumn(
                    "Average", format="%.2f"
                ),
                "median": st.column_config.NumberColumn("Median", format="%.2f"),
                "minimum": st.column_config.NumberColumn("Minimum", format="%.2f"),
                "maximum": st.column_config.NumberColumn("Maximum", format="%.2f"),
                "std_dev": st.column_config.NumberColumn("Std Dev", format="%.2f"),
                "p25": st.column_config.NumberColumn(
                    "25th Percentile", format="%.2f"
                ),
                "p75": st.column_config.NumberColumn(
                    "75th Percentile", format="%.2f"
                ),
            },
        )

        st.download_button(
            "⬇️ Download KPI Analysis",
            data=filtered_df[display_columns].to_csv(index=False),
            file_name="kpi_analysis.csv",
            mime="text/csv",
            key="download_kpi_analysis",
        )