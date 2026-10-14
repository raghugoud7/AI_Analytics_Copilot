import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


def render_summary_tab(summary: dict) -> None:
    st.subheader("📌 Data Summary")

    if not summary.get("success", False):
        st.error(summary.get("error", "Data summary analysis failed."))
        return

    overview = summary.get("overview", {})
    quality = summary.get("data_quality", {})
    column_analysis = summary.get("column_analysis", {})

    total_rows = overview.get("total_rows", 0)
    sample_rows = overview.get("sample_rows", 0)
    total_columns = overview.get("total_columns", 0)
    numeric_columns = overview.get("numeric_columns", 0)
    categorical_columns = overview.get("categorical_columns", 0)
    datetime_columns = overview.get("datetime_columns", 0)

    metrics = [
        ("Total Rows", f"{total_rows:,}"),
        ("Sample Rows", f"{sample_rows:,}"),
        ("Columns", f"{total_columns:,}"),
        ("Numeric", f"{numeric_columns:,}"),
        ("Categorical", f"{categorical_columns:,}"),
        ("Datetime", f"{datetime_columns:,}"),
    ]

    for column, (label, value) in zip(st.columns(len(metrics)), metrics):
        column.metric(label, value)

    with st.expander("🎛️ Chart Filters", expanded=False):
        f1, f2, f3, f4 = st.columns(4)

        selected_types = f1.multiselect(
            "Column Types",
            ["Numeric", "Categorical", "Datetime"],
            default=["Numeric", "Categorical", "Datetime"],
            key="summary_column_types",
        )

        missing_threshold = f2.slider(
            "Minimum Missing %",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=1.0,
            key="summary_missing_threshold",
        )

        top_n = f3.slider(
            "Top Columns",
            min_value=5,
            max_value=50,
            value=10,
            step=5,
            key="summary_top_n",
        )

        sort_order = f4.selectbox(
            "Sort Order",
            ["Highest first", "Lowest first"],
            key="summary_sort_order",
        )

        chart_type = st.radio(
            "Missing-Value Chart",
            ["Bar", "Treemap"],
            horizontal=True,
            key="summary_missing_chart_type",
        )

    ascending = sort_order == "Lowest first"

    if total_rows and sample_rows:
        coverage = min(sample_rows / total_rows * 100, 100)

        st.markdown("### 📊 Analysis Coverage")
        st.progress(coverage / 100)
        st.caption(
            f"Analysis uses {sample_rows:,} sampled rows from {total_rows:,} "
            f"total rows ({coverage:.2f}% coverage)."
        )

    st.markdown("### 🔍 Data Quality Overview")

    missing_values = quality.get("missing_values", 0)
    missing_percentage = quality.get("missing_percentage", 0)
    duplicate_rows = quality.get("duplicate_rows", 0)
    duplicate_percentage = quality.get("duplicate_percentage", 0)

    quality_metrics = [
        ("Missing Values", f"{missing_values:,}"),
        ("Missing %", f"{missing_percentage:.2f}%"),
        ("Duplicate Rows", f"{duplicate_rows:,}"),
        ("Duplicate %", f"{duplicate_percentage:.2f}%"),
    ]

    for column, (label, value) in zip(st.columns(len(quality_metrics)), quality_metrics):
        column.metric(label, value)

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 🧱 Column Types")

        type_counts = {
            "Numeric": numeric_columns,
            "Categorical": categorical_columns,
            "Datetime": datetime_columns,
        }

        type_df = pd.DataFrame(
            [
                {"type": column_type, "count": type_counts[column_type]}
                for column_type in selected_types
                if type_counts.get(column_type, 0) > 0
            ]
        )

        if type_df.empty:
            st.info("Select at least one available column type.")
        else:
            fig = px.pie(
                type_df,
                names="type",
                values="count",
                hole=0.55,
                color="type",
                color_discrete_map={
                    "Numeric": "#2563EB",
                    "Categorical": "#7C3AED",
                    "Datetime": "#0891B2",
                },
                title="Column Type Distribution",
            )
            fig.update_traces(textposition="inside", textinfo="percent+label")
            fig.update_layout(height=420, legend_title_text="Column Type")
            st.plotly_chart(fig, width="stretch")

    with chart_col2:
        st.markdown("### ✅ Data Completeness")

        completeness = max(min(100 - missing_percentage, 100), 0)

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=completeness,
                number={"suffix": "%", "valueformat": ".2f"},
                title={"text": "Complete Cells"},
                gauge={
                    "axis": {"range": [0, 100]},
                    "bar": {"color": "#16A34A"},
                    "steps": [
                        {"range": [0, 60], "color": "#FEE2E2"},
                        {"range": [60, 85], "color": "#FEF3C7"},
                        {"range": [85, 100], "color": "#DCFCE7"},
                    ],
                    "threshold": {
                        "line": {"color": "#DC2626", "width": 4},
                        "thickness": 0.75,
                        "value": 95,
                    },
                },
            )
        )

        fig.update_layout(height=420, margin={"l": 40, "r": 40, "t": 80, "b": 30})
        st.plotly_chart(fig, width="stretch")

    high_null_columns = column_analysis.get("high_null_columns", {})

    if high_null_columns:
        null_df = pd.DataFrame(
            [
                {"column": column, "missing_percentage": percentage}
                for column, percentage in high_null_columns.items()
            ]
        )

        null_df = (
            null_df[null_df["missing_percentage"] >= missing_threshold]
            .sort_values("missing_percentage", ascending=ascending)
            .head(top_n)
        )

        st.markdown("### ⚠️ Columns With Missing Values")

        if null_df.empty:
            st.info(f"No columns meet the {missing_threshold:.0f}% missing threshold.")
        elif chart_type == "Bar":
            fig = px.bar(
                null_df,
                x="missing_percentage",
                y="column",
                orientation="h",
                color="missing_percentage",
                text="missing_percentage",
                color_continuous_scale="Reds",
                title="Columns by Missing Percentage",
            )

            fig.update_traces(
                texttemplate="%{text:.2f}%",
                textposition="outside",
            )

            fig.update_layout(
                height=max(400, len(null_df) * 38),
                xaxis_title="Missing Percentage",
                yaxis_title="Column",
            )

            st.plotly_chart(fig, width="stretch")
        else:
            fig = px.treemap(
                null_df,
                path=["column"],
                values="missing_percentage",
                color="missing_percentage",
                color_continuous_scale="Reds",
                title="Missing-Value Treemap",
            )

            fig.update_traces(
                texttemplate="<b>%{label}</b><br>%{value:.2f}% missing"
            )

            fig.update_layout(height=500)
            st.plotly_chart(fig, width="stretch")

        with st.expander("View Missing-Value Details"):
            st.dataframe(null_df, width="stretch", hide_index=True)
            st.download_button(
                "⬇️ Download Missing-Value Analysis",
                null_df.to_csv(index=False),
                "missing_value_analysis.csv",
                "text/csv",
            )

    high_cardinality_columns = column_analysis.get("high_cardinality_columns", {})

    if high_cardinality_columns:
        cardinality_df = pd.DataFrame(
            [
                {"column": column, "distinct_values": count}
                for column, count in high_cardinality_columns.items()
            ]
        )

        cardinality_df = cardinality_df.sort_values(
            "distinct_values", ascending=ascending
        ).head(top_n)

        st.markdown("### 🔢 High-Cardinality Columns")

        fig = px.bar(
            cardinality_df,
            x="distinct_values",
            y="column",
            orientation="h",
            color="distinct_values",
            text="distinct_values",
            color_continuous_scale="Blues",
            title="Distinct Values by Column",
        )

        fig.update_traces(textposition="outside")

        fig.update_layout(
            height=max(400, len(cardinality_df) * 38),
            xaxis_title="Distinct Values",
            yaxis_title="Column",
        )

        st.plotly_chart(fig, width="stretch")

        with st.expander("View Cardinality Details"):
            st.dataframe(cardinality_df, width="stretch", hide_index=True)

    constant_columns = quality.get("constant_columns", [])

    if constant_columns:
        with st.expander(f"⚠️ Constant Columns ({len(constant_columns)})"):
            st.warning(
                "Constant columns contain one distinct value and may provide "
                "limited analytical value."
            )
            st.write(constant_columns)

    numeric_names = summary.get("top_numeric_columns", [])
    categorical_names = summary.get("top_categorical_columns", [])

    with st.expander("📋 Column-Type Details"):
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### Numeric Columns")
            st.write(numeric_names or "No numeric columns found.")

        with col2:
            st.markdown("#### Categorical Columns")
            st.write(categorical_names or "No categorical columns found.")

    st.caption(
        f"Sample DataFrame memory usage: {summary.get('memory_mb', 0):,.2f} MB"
    )