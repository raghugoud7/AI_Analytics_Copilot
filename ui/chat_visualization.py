# ui/chat_visualization.py

import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from utils.privacy import remove_sensitive_columns


SUPPORTED_CHARTS = {
    "area",
    "bar",
    "box",
    "histogram",
    "line",
    "pie",
    "scatter",
}


def _validate_column(
    df: pd.DataFrame,
    column,
    field: str,
    required: bool = False,
) -> str | None:
    if column is None or column == "":
        if required:
            raise ValueError(f"Chart specification requires '{field}'.")
        return None

    if not isinstance(column, str):
        raise ValueError(f"Chart field '{field}' must be a column name.")

    if column not in df.columns:
        raise ValueError(
            f"Column '{column}' is unavailable for '{field}'. "
            f"Available columns: {df.columns.tolist()}"
        )

    return column


def _numeric_column(df: pd.DataFrame, column: str) -> None:
    original = df[column]
    converted = pd.to_numeric(original, errors="coerce")

    if (original.notna() & converted.isna()).any():
        raise ValueError(f"Column '{column}' contains non-numeric values.")

    df[column] = converted.replace([float("inf"), float("-inf")], float("nan"))

    if df[column].notna().sum() == 0:
        raise ValueError(f"Column '{column}' has no finite numeric values.")


def build_chart(df: pd.DataFrame, chart: dict):
    """Build a Plotly figure without creating Streamlit widgets."""
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("No visualization data is available.")

    if not isinstance(chart, dict):
        raise ValueError("Chart specification must be a dictionary.")

    working_df = remove_sensitive_columns(df).copy()

    if working_df.empty:
        raise ValueError("No privacy-approved visualization columns are available.")

    if not working_df.columns.is_unique:
        raise ValueError("Query results contain duplicate column names.")

    chart_type = str(chart.get("type") or "").lower().strip()
    title = str(chart.get("title") or "Visualization")

    if chart_type not in SUPPORTED_CHARTS:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    # Convention:
    # x = category, time, or input field
    # y = numeric measure
    # Horizontal bars swap axes only when building the figure.
    x = _validate_column(
        working_df,
        chart.get("x"),
        "x",
        required=chart_type != "box",
    )
    y = _validate_column(
        working_df,
        chart.get("y"),
        "y",
        required=chart_type != "histogram",
    )
    color = _validate_column(working_df, chart.get("color"), "color")
    size = _validate_column(working_df, chart.get("size"), "size")

    orientation = str(chart.get("orientation") or "vertical").lower().strip()
    show_values = chart.get("show_values", True) is True

    if chart_type == "bar" and orientation not in {"vertical", "horizontal"}:
        raise ValueError("Bar orientation must be 'vertical' or 'horizontal'.")

    if y is not None and chart_type != "histogram":
        _numeric_column(working_df, y)

    if chart_type in {"histogram", "scatter"} and x is not None:
        _numeric_column(working_df, x)

    if chart_type == "scatter" and size is not None:
        _numeric_column(working_df, size)

        if working_df[size].isna().any() or (working_df[size] < 0).any():
            raise ValueError("Scatter size values must be finite and non-negative.")

    required_values = [y] if chart_type == "box" else [x]

    if chart_type not in {"histogram", "box"}:
        required_values.append(y)

    working_df = working_df.dropna(
        subset=[column for column in required_values if column is not None]
    )

    if working_df.empty:
        raise ValueError("No valid rows remain for the requested chart.")

    if chart_type in {"line", "area"}:
        working_df = working_df.sort_values(x)

    if chart_type == "bar":
        horizontal = orientation == "horizontal"

        fig = px.bar(
            working_df,
            x=y if horizontal else x,
            y=x if horizontal else y,
            color=color,
            orientation="h" if horizontal else "v",
            text=y if show_values else None,
            title=title,
        )

        if show_values:
            fig.update_traces(
                texttemplate="%{text:.2f}",
                textposition="auto",
            )

        category_axis = {"categoryorder": "array", "categoryarray": working_df[x].tolist()}

        if horizontal:
            fig.update_yaxes(**category_axis, autorange="reversed")
        else:
            fig.update_xaxes(**category_axis)

    elif chart_type == "line":
        fig = px.line(
            working_df,
            x=x,
            y=y,
            color=color,
            markers=True,
            title=title,
        )

    elif chart_type == "area":
        fig = px.area(
            working_df,
            x=x,
            y=y,
            color=color,
            title=title,
        )

    elif chart_type == "scatter":
        fig = px.scatter(
            working_df,
            x=x,
            y=y,
            color=color,
            size=size,
            title=title,
        )

    elif chart_type == "pie":
        if (working_df[y] < 0).any() or working_df[y].sum() <= 0:
            raise ValueError("Pie values must be non-negative with a positive total.")

        fig = px.pie(
            working_df,
            names=x,
            values=y,
            color=color,
            hole=0.35,
            title=title,
        )

        if show_values:
            fig.update_traces(textinfo="label+percent")

    elif chart_type == "histogram":
        bins = chart.get("nbins", 40)

        if isinstance(bins, bool) or not isinstance(bins, int):
            raise ValueError("Histogram nbins must be an integer.")

        fig = px.histogram(
            working_df,
            x=x,
            color=color,
            nbins=max(5, min(bins, 200)),
            title=title,
        )

    else:
        fig = px.box(
            working_df,
            x=x,
            y=y,
            color=color,
            points="outliers",
            title=title,
        )

    fig.update_layout(
        template="plotly_white",
        height=520,
        margin={"l": 20, "r": 20, "t": 70, "b": 20},
        legend_title_text=color or "",
    )

    return fig


def render_chat_visualization(
    result: list[dict],
    chart: dict,
    key_prefix: str | None = None,
) -> None:
    """Optional standalone renderer; app.py can call build_chart directly."""
    widget_key = key_prefix or f"visualization_{uuid.uuid4().hex}"

    try:
        df = remove_sensitive_columns(pd.DataFrame(result or []))

        if df.empty:
            st.info("The visualization query returned no data.")
            return

        fig = build_chart(df, chart)

        st.plotly_chart(
            fig,
            width="stretch",
            key=f"{widget_key}_chart",
        )

        with st.expander("View Visualization Data"):
            st.dataframe(df, width="stretch", hide_index=True)

            st.download_button(
                "Download Visualization Data",
                data=df.to_csv(index=False),
                file_name="visualization_data.csv",
                mime="text/csv",
                key=f"{widget_key}_download",
            )

    except Exception as ex:
        st.error(f"Unable to render visualization: {ex}")