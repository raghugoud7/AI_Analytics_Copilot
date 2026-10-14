# ui/segment_tab.py

import hashlib

import pandas as pd
import plotly.express as px
import streamlit as st


SIGNIFICANCE_COLORS = {
    "Highly Significant": "#059669",
    "Significant": "#2563EB",
    "Not Significant": "#94A3B8",
    "Insufficient Sample": "#F59E0B",
    "Test Unavailable": "#64748B",
}


def format_chart(fig, title: str, rows: int):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=max(350, min(850, rows * 38 + 100)),
        margin={"l": 20, "r": 30, "t": 70, "b": 30},
        legend_title_text="",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def prepare_segments(records) -> pd.DataFrame:
    if not isinstance(records, list) or not records:
        return pd.DataFrame()

    frame = pd.DataFrame(records)

    if not {"segment", "avg_kpi", "record_count"}.issubset(frame.columns):
        return pd.DataFrame()

    numeric_fields = [
        "avg_kpi",
        "record_count",
        "segment_percentage",
        "difference_from_average",
        "sample_size",
        "comparison_size",
        "p_value",
        "adjusted_p_value",
    ]

    for column in numeric_fields:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce").replace(
                [float("inf"), float("-inf")],
                float("nan"),
            )

    frame = frame.dropna(subset=["segment", "avg_kpi", "record_count"]).copy()
    frame["segment"] = frame["segment"].astype(str)

    # Never infer adjusted significance from a raw p-value.
    if "adjusted_p_value" in frame.columns:
        frame["significant"] = frame["adjusted_p_value"].le(0.05).fillna(False)
    elif "significant" in frame.columns:
        frame["significant"] = frame["significant"].eq(True)
    else:
        frame["significant"] = False

    if "significance" not in frame.columns:
        frame["significance"] = "Test Unavailable"

    frame["significance"] = frame["significance"].fillna("Test Unavailable")
    frame["significance_display"] = frame["significance"].where(
        frame["significance"].isin(SIGNIFICANCE_COLORS),
        "Test Unavailable",
    )

    return frame


def render_segment_tab(
    analysis: dict,
    key_prefix: str = "segments",
) -> None:
    st.subheader("📊 Segment Analysis")

    if not isinstance(analysis, dict):
        st.error("Invalid segment analysis response.")
        return

    if not analysis.get("success", False):
        st.warning(analysis.get("error") or "Segment analysis is unavailable.")
        return

    dimensions = analysis.get("segments") or {}
    skipped = analysis.get("skipped_dimensions") or {}

    st.caption(
        f"Target measure: {analysis.get('target_kpi', 'N/A')} | "
        f"Analyzed dimensions: {analysis.get('dimensions_analyzed', len(dimensions))}"
    )

    if isinstance(skipped, dict) and skipped:
        with st.expander(f"Skipped Dimensions ({len(skipped)})"):
            st.dataframe(
                [
                    {"dimension": dimension, "reason": reason}
                    for dimension, reason in skipped.items()
                ],
                width="stretch",
                hide_index=True,
            )

    if not isinstance(dimensions, dict) or not dimensions:
        st.info(
            analysis.get("message")
            or "No eligible segment comparisons were found in the loaded sample."
        )
        return

    higher_is_better = analysis.get("higher_is_better", True)
    direction = "Higher values preferred" if higher_is_better else "Lower values preferred"

    st.caption(
        f"{direction}. Best and worst refer to eligible groups, not excluded groups. "
        "Statistical tests are exploratory and assume independent observations."
    )

    if analysis.get("significance_method"):
        st.caption(
            f"Testing method: {analysis['significance_method']}. "
            "Significance labels use adjusted p-values; raw p-values are shown separately."
        )

    # Include dimension names in widget scope when switching datasets.
    dimension_token = hashlib.sha256(
        repr(tuple(dimensions)).encode("utf-8")
    ).hexdigest()[:10]
    widget_scope = f"{key_prefix}_{dimension_token}"

    dimension = st.selectbox(
        "Select a dimension",
        options=list(dimensions),
        key=f"{widget_scope}_dimension",
    )

    details = dimensions[dimension]

    if not isinstance(details, dict):
        st.warning("Invalid dimension results.")
        return

    records = details.get("all_segments") or details.get("top_segments") or []
    segment_df = prepare_segments(records)

    if segment_df.empty:
        st.info("No valid segment records are available for this dimension.")
        return

    overall = pd.to_numeric(
        details.get("overall_kpi", analysis.get("overall_kpi")),
        errors="coerce",
    )

    if (
        "difference_from_average" not in segment_df.columns
        and pd.notna(overall)
    ):
        segment_df["difference_from_average"] = segment_df["avg_kpi"] - overall

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Distinct Categories", details.get("cardinality", 0))
    c2.metric("Overall Sample Average", f"{overall:,.2f}" if pd.notna(overall) else "N/A")
    c3.metric("Eligible Groups", details.get("eligible_segment_count", len(segment_df)))
    c4.metric("Missing Dimension Rows", details.get("missing_dimension_records", 0))

    # ==================================================
    # BEST / WORST ACROSS ALL ELIGIBLE GROUPS
    # ==================================================

    left, right = st.columns(2)

    for container, label, field in [
        (left, "Best Eligible Segment", "best_segment"),
        (right, "Worst Eligible Segment", "worst_segment"),
    ]:
        with container:
            item = details.get(field)

            if not isinstance(item, dict):
                st.info(f"No {label.lower()} is available.")
                continue

            value = pd.to_numeric(item.get("avg_kpi"), errors="coerce")
            difference = pd.to_numeric(
                item.get("difference_from_average"),
                errors="coerce",
            )

            st.markdown(f"#### {label}")
            st.markdown(f"**{item.get('segment', 'N/A')}**")
            st.metric(
                "Average",
                f"{value:,.2f}" if pd.notna(value) else "N/A",
                delta=f"{difference:+.2f} vs overall" if pd.notna(difference) else None,
                delta_color="normal" if higher_is_better else "inverse",
            )
            st.caption(
                f"Records: {item.get('record_count', 0):,} | "
                f"{item.get('significance', 'Test unavailable')}"
            )

    # ==================================================
    # DISPLAY FILTERS
    # ==================================================

    dimension_key = hashlib.sha256(dimension.encode("utf-8")).hexdigest()[:10]
    control_key = f"{widget_scope}_{dimension_key}"

    with st.expander("Chart Filters", expanded=True):
        f1, f2, f3 = st.columns(3)

        min_records = f1.number_input(
            "Minimum group records",
            min_value=1,
            value=1,
            step=1,
            key=f"{control_key}_records",
        )

        top_n = f2.selectbox(
            "Maximum displayed groups",
            options=[5, 10, 20, 50, 100],
            index=1,
            key=f"{control_key}_top_n",
        )

        sort_by = f3.selectbox(
            "Rank by",
            options=["Performance", "Record count", "Absolute difference"],
            key=f"{control_key}_sort",
        )

        significant_only = st.checkbox(
            "Show statistically significant groups only",
            key=f"{control_key}_significant",
        )

    filtered_df = segment_df.loc[
        segment_df["record_count"] >= min_records
    ].copy()

    if significant_only:
        filtered_df = filtered_df.loc[filtered_df["significant"]].copy()

    if filtered_df.empty:
        st.info("No groups meet the display filters. Try relaxing the filters.")
        return

    if sort_by == "Record count":
        filtered_df = filtered_df.sort_values("record_count", ascending=False)
    elif sort_by == "Absolute difference":
        if "difference_from_average" in filtered_df.columns:
            filtered_df = filtered_df.loc[
                filtered_df["difference_from_average"].abs().sort_values(
                    ascending=False
                ).index
            ]
        else:
            st.info("Difference values are unavailable; ranking by performance.")
            filtered_df = filtered_df.sort_values(
                "avg_kpi",
                ascending=not higher_is_better,
            )
    else:
        filtered_df = filtered_df.sort_values(
            "avg_kpi",
            ascending=not higher_is_better,
        )

    display_df = filtered_df.head(top_n).copy()
    st.caption(f"Displaying {len(display_df)} of {len(segment_df)} available eligible groups.")

    hover_fields = [
        column
        for column in [
            "record_count",
            "sample_size",
            "comparison_size",
            "segment_percentage",
            "p_value",
            "adjusted_p_value",
        ]
        if column in display_df.columns
    ]

    # ==================================================
    # PERFORMANCE WITH OVERALL BASELINE
    # ==================================================

    fig = px.bar(
        display_df,
        x="avg_kpi",
        y="segment",
        orientation="h",
        color="significance_display",
        text="avg_kpi",
        hover_data=hover_fields,
        color_discrete_map=SIGNIFICANCE_COLORS,
        labels={"significance_display": "Significance"},
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="auto")
    fig = format_chart(fig, f"{dimension}: Average KPI by Segment", len(display_df))
    fig.update_xaxes(title="Average KPI")
    fig.update_yaxes(title=dimension)

    if pd.notna(overall):
        fig.add_vline(
            x=float(overall),
            line_dash="dash",
            line_color="#334155",
            annotation_text="Overall average",
        )

    st.plotly_chart(
        fig,
        width="stretch",
        key=f"{control_key}_performance",
    )

    # ==================================================
    # DIFFERENCE FROM OVERALL
    # ==================================================

    if "difference_from_average" in display_df.columns:
        difference_df = display_df.dropna(subset=["difference_from_average"]).copy()
        difference_df["direction"] = difference_df["difference_from_average"].apply(
            lambda value: "Above overall" if value >= 0 else "Below overall"
        )

        if not difference_df.empty:
            fig = px.bar(
                difference_df,
                x="difference_from_average",
                y="segment",
                orientation="h",
                color="direction",
                text="difference_from_average",
                color_discrete_map={
                    "Above overall": "#2563EB",
                    "Below overall": "#F59E0B",
                },
                hover_data=hover_fields,
            )
            fig.update_traces(texttemplate="%{text:+.2f}", textposition="auto")
            fig.add_vline(x=0, line_color="#64748B")
            fig = format_chart(
                fig,
                "Difference from Overall Sample Average",
                len(difference_df),
            )
            fig.update_xaxes(title="Difference in KPI units")
            fig.update_yaxes(title=dimension)

            st.plotly_chart(
                fig,
                width="stretch",
                key=f"{control_key}_difference",
            )

    # ==================================================
    # SAMPLE SHARE: NO PIE RENORMALIZATION
    # ==================================================

    if "segment_percentage" in display_df.columns:
        share_df = display_df.dropna(subset=["segment_percentage"]).sort_values(
            "segment_percentage",
            ascending=False,
        )

        if not share_df.empty:
            fig = px.bar(
                share_df,
                x="segment_percentage",
                y="segment",
                orientation="h",
                text="segment_percentage",
                hover_data=["record_count"],
            )
            fig.update_traces(
                marker_color="#7C3AED",
                texttemplate="%{text:.2f}%",
                textposition="auto",
            )
            fig = format_chart(fig, "Segment Share of All Loaded Rows", len(share_df))
            fig.update_xaxes(title="Loaded sample share (%)", range=[0, 100])
            fig.update_yaxes(title=dimension)

            st.plotly_chart(
                fig,
                width="stretch",
                key=f"{control_key}_share",
            )
            st.caption(
                "Percentages use all loaded rows as the denominator. "
                "Filtered, missing, and excluded groups are not displayed, "
                "so displayed percentages may total less than 100%."
            )

    # ==================================================
    # DETAILS AND DOWNLOAD
    # ==================================================

    export_df = display_df.drop(columns=["significance_display"], errors="ignore").copy()
    export_df.insert(0, "dimension", dimension)

    with st.expander("View Displayed Segment Details"):
        st.dataframe(export_df, width="stretch", hide_index=True)

    st.download_button(
        "Download Displayed Segment Results",
        data=export_df.to_csv(index=False),
        file_name="segment_analysis.csv",
        mime="text/csv",
        key=f"{control_key}_download",
    )

    st.caption(
        "Display filters do not recalculate averages, significance tests, "
        "or best/worst segments. Results apply to the loaded sample."
    )