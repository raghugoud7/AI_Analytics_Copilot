# ui/drivers_tab.py

import pandas as pd
import plotly.express as px
import streamlit as st

from analytics.driver_analyzer import DriverAnalyzer
from utils.privacy import remove_sensitive_columns


STRENGTH_COLORS = {
    "Very Strong": "#006400",
    "Strong": "#2E8B57",
    "Moderate": "#FFA500",
    "Weak": "#FF6347",
    "Very Weak": "#DC143C",
}


def get_strength(correlation: float) -> str:
    value = abs(float(correlation))

    if value >= 0.80:
        return "Very Strong"
    if value >= 0.60:
        return "Strong"
    if value >= 0.40:
        return "Moderate"
    if value >= 0.20:
        return "Weak"

    return "Very Weak"


def format_chart(fig, title: str, height: int = 500):
    fig.update_layout(
        title=title,
        template="plotly_white",
        height=height,
        font={"size": 14},
        title_font={"size": 18},
        margin={"l": 20, "r": 20, "t": 60, "b": 20},
        legend_title_text="Strength",
    )
    return fig


def prepare_drivers(records, positive: bool) -> pd.DataFrame:
    columns = ["driver", "correlation", "strength", "sample_size"]

    if not isinstance(records, list) or not records:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(records)

    if not {"driver", "correlation"}.issubset(frame.columns):
        return pd.DataFrame(columns=columns)

    frame = frame.copy()
    frame["correlation"] = pd.to_numeric(frame["correlation"], errors="coerce")
    frame["correlation"] = frame["correlation"].replace(
        [float("inf"), float("-inf")],
        float("nan"),
    )
    frame = frame.dropna(subset=["driver", "correlation"])
    frame = frame[frame["correlation"].between(-1, 1)]

    mask = frame["correlation"] > 0 if positive else frame["correlation"] < 0
    frame = frame.loc[mask].copy()
    frame["strength"] = frame["correlation"].apply(get_strength)

    if "sample_size" not in frame.columns:
        frame["sample_size"] = pd.NA

    return frame[columns].sort_values("correlation", ascending=not positive)


def render_drivers_tab(
    df: pd.DataFrame,
    key_prefix: str = "drivers",
) -> None:
    st.subheader("🎯 Driver Analysis")
    st.caption(
        "Explore linear associations with a business measure. "
        "Correlation does not establish causation or statistical significance."
    )

    if not isinstance(df, pd.DataFrame) or df.empty:
        st.warning("No dataset is available.")
        return

    safe_df = remove_sensitive_columns(df)

    if safe_df.empty:
        st.warning("No privacy-approved columns are available.")
        return

    if not safe_df.columns.is_unique:
        st.error("Duplicate column names are not supported.")
        return

    numeric_df = safe_df.select_dtypes(include="number").replace(
        [float("inf"), float("-inf")],
        float("nan"),
    )

    eligible_targets = [
        column
        for column in numeric_df.columns
        if numeric_df[column].count() >= 3
        and numeric_df[column].nunique(dropna=True) >= 2
    ]

    if len(eligible_targets) < 2:
        st.info("At least two varying numeric columns are required.")
        return

    # ==================================================
    # TARGET AND FILTERS
    # ==================================================

    target = st.selectbox(
        "Select the business measure to analyze",
        options=eligible_targets,
        index=None,
        placeholder="Choose a target measure",
        key=f"{key_prefix}_target",
    )

    st.caption(
        "Choose a business measure, not an identifier or technical key. "
        "Numeric columns are candidates, not automatically meaningful KPIs."
    )

    c1, c2, c3 = st.columns(3)

    min_records = c1.number_input(
        "Minimum paired records",
        min_value=3,
        value=30,
        step=1,
        key=f"{key_prefix}_min_records",
    )

    min_correlation = c2.slider(
        "Minimum absolute correlation",
        min_value=0.0,
        max_value=1.0,
        value=0.30,
        step=0.05,
        key=f"{key_prefix}_min_correlation",
    )

    top_n = c3.selectbox(
        "Top relationships per direction",
        options=[5, 10, 15, 20],
        index=1,
        key=f"{key_prefix}_top_n",
    )

    if target is None:
        st.info("Select a target measure to start.")
        return

    # ==================================================
    # ANALYSIS
    # ==================================================

    try:
        with st.spinner("Analyzing relationships..."):
            driver_analysis = DriverAnalyzer().analyze(
                df=safe_df,
                target_col=target,
                top_n=int(top_n),
                min_records=int(min_records),
                min_correlation=float(min_correlation),
            )
    except Exception as ex:
        st.error(f"Driver analysis failed: {ex}")
        return

    if not isinstance(driver_analysis, dict):
        st.error("Invalid driver analysis response.")
        return

    if not driver_analysis.get("success", False):
        st.warning(driver_analysis.get("error") or "Driver analysis unavailable.")
        return

    positive_df = prepare_drivers(
        driver_analysis.get("top_positive_drivers"),
        positive=True,
    )
    negative_df = prepare_drivers(
        driver_analysis.get("top_negative_drivers"),
        positive=False,
    )

    # ==================================================
    # SUMMARY CARDS
    # ==================================================

    c1, c2, c3 = st.columns(3)
    c1.metric("Target Measure", str(target))
    c2.metric("Qualifying Relationships", driver_analysis.get("driver_count", 0))
    c3.metric("Displayed Relationships", len(positive_df) + len(negative_df))

    for label, frame in [
        ("Strongest Positive Association", positive_df),
        ("Strongest Negative Association", negative_df),
    ]:
        if not frame.empty:
            row = frame.iloc[0]
            st.info(
                f"**{label}: {row['driver']}** | "
                f"Correlation: {row['correlation']:+.3f} | "
                f"Strength: {row['strength']}"
            )

    # ==================================================
    # POSITIVE / NEGATIVE CHARTS
    # ==================================================

    for direction, frame in [
        ("Positive", positive_df),
        ("Negative", negative_df),
    ]:
        st.markdown(f"### {direction} Associations")

        if frame.empty:
            st.info(f"No {direction.lower()} associations meet the selected filters.")
            continue

        plot_df = frame.copy()
        plot_df["magnitude"] = plot_df["correlation"].abs()
        plot_df = plot_df.sort_values("magnitude", ascending=False)

        fig = px.bar(
            plot_df,
            x="correlation",
            y="driver",
            orientation="h",
            color="strength",
            text="correlation",
            hover_data={"sample_size": True, "magnitude": False},
            color_discrete_map=STRENGTH_COLORS,
        )
        fig.update_traces(texttemplate="%{text:.3f}", textposition="auto")
        fig = format_chart(
            fig,
            f"{direction} Associations with {target}",
            height=max(350, len(plot_df) * 40),
        )
        fig.update_xaxes(title="Pearson Correlation", range=[-1.05, 1.05])
        fig.update_yaxes(
            title="Measure",
            categoryorder="array",
            categoryarray=plot_df["driver"].tolist(),
            autorange="reversed",
        )

        st.plotly_chart(
            fig,
            width="stretch",
            key=f"{key_prefix}_{direction.lower()}_chart",
        )

        with st.expander(f"{direction} Relationship Details"):
            st.dataframe(frame, width="stretch", hide_index=True)

    # ==================================================
    # DISTRIBUTION AND DOWNLOAD
    # ==================================================

    frames = [frame for frame in [positive_df, negative_df] if not frame.empty]

    if frames:
        displayed_drivers = pd.concat(frames, ignore_index=True)

        st.markdown("### 📊 Displayed Correlation Distribution")

        fig = px.histogram(
            displayed_drivers,
            x="correlation",
            color="strength",
            nbins=15,
            color_discrete_map=STRENGTH_COLORS,
        )
        fig = format_chart(fig, "Distribution of Displayed Relationships")
        fig.update_xaxes(title="Pearson Correlation", range=[-1.05, 1.05])
        fig.update_yaxes(title="Relationship Count")

        st.plotly_chart(
            fig,
            width="stretch",
            key=f"{key_prefix}_distribution",
        )

        export_df = displayed_drivers.copy()
        export_df.insert(0, "target", target)

        st.download_button(
            "Download Displayed Relationships",
            data=export_df.to_csv(index=False),
            file_name="driver_analysis.csv",
            mime="text/csv",
            key=f"{key_prefix}_download",
        )

        st.caption(
            "Charts and downloads include the displayed top relationships, "
            "not every qualifying relationship."
        )

        # Recommendations are investigation steps, not causal claims.
        st.markdown("### 🔎 Recommended Next Checks")
        st.markdown(
            "- Review paired sample sizes and missing-value patterns.\n"
            "- Check whether related measures are components of the target itself.\n"
            "- Exclude identifiers, technical keys, and leakage-prone fields.\n"
            "- Compare relationships across time periods and business segments.\n"
            "- Validate findings before recommending operational changes."
        )

    # ==================================================
    # SKIPPED COLUMNS
    # ==================================================

    skipped = driver_analysis.get("skipped_columns") or {}

    if isinstance(skipped, dict) and skipped:
        with st.expander("Skipped Columns and Reasons"):
            skipped_df = pd.DataFrame(
                [{"column": column, "reason": reason} for column, reason in skipped.items()]
            )
            st.dataframe(skipped_df, width="stretch", hide_index=True)

    if driver_analysis.get("message"):
        st.caption(driver_analysis["message"])