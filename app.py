# app.py

import re
import time
import uuid

import pandas as pd
import plotly.express as px
import streamlit as st

from agents.orchestrator import AnalyticsOrchestrator
from analytics.data_analysis_orchestrator import DataAnalysisOrchestrator
from config.privacy import SENSITIVE_COLUMNS
from database.query_executor import QueryExecutor
from database.schema_extractor import SchemaExtractor
from ui.chat_visualization import build_chart
from ui.correlation_tab import render_correlation_tab
from ui.drivers_tab import render_drivers_tab
from ui.kpis_tab import render_kpis_tab
from ui.outliers_tab import render_outlier_tab
from ui.profiling_tab import render_profiling_tab
from ui.segment_tab import render_segment_tab
from ui.summary_tab import render_summary_tab
from ui.trend_tab import render_trend_tab
from utils.privacy import remove_sensitive_columns


# ==========================================================
# PAGE CONFIGURATION
# ==========================================================

st.set_page_config(
    page_title="AI Analytics Copilot",
    page_icon="📊",
    layout="wide",
)

# ==========================================================
# COMPACT SIDEBAR
# ==========================================================

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
        padding-top: 0.75rem;
        padding-bottom: 0.75rem;
    }

    [data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
        gap: 0.55rem;
    }

    [data-testid="stSidebar"] h1 {
        font-size: 1.35rem;
        padding-top: 0;
        padding-bottom: 0.35rem;
    }

    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        font-size: 1.05rem;
        padding-top: 0.25rem;
        padding-bottom: 0.25rem;
    }

    [data-testid="stSidebar"] hr {
        margin: 0.4rem 0;
    }

    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {
        margin-bottom: 0;
        font-size: 0.9rem;
    }

    [data-testid="stSidebar"] [data-testid="stButton"] button {
        min-height: 2.2rem;
        padding: 0.25rem 0.65rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================================
# SESSION STATE
# ==========================================================

DEFAULT_STATE = {
    "metadata_df": None,
    "sample_df": None,
    "row_count": 0,
    "schema_name": None,
    "table_name": None,
    "messages": [],
    "analytics_history": [],
    "last_analysis": None,
    "last_response": None,
    "generated_insight": None,
    "brands": [],
    "selected_brand": None,
    "loaded_brand": None,
    "brands_scope": None,
    "dataset_version": None,
    "analysis_result": None,
    "analysis_version": None,
    "chat_orchestrator": None,
    "chat_orchestrator_scope": None,
}

for key, default in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ==========================================================
# RESOURCES
# ==========================================================

@st.cache_resource
def get_query_executor():
    return QueryExecutor()


@st.cache_resource
def get_data_analyzer():
    return DataAnalysisOrchestrator()


def get_orchestrator():
    """Keep chat memory isolated to this session and loaded dataset."""
    scope = (
        st.session_state.schema_name,
        st.session_state.table_name,
        st.session_state.loaded_brand,
    )

    if (
        st.session_state.chat_orchestrator is None
        or st.session_state.chat_orchestrator_scope != scope
    ):
        st.session_state.chat_orchestrator = AnalyticsOrchestrator(
            enable_redis=False,
        )
        st.session_state.chat_orchestrator_scope = scope

    return st.session_state.chat_orchestrator


# ==========================================================
# SQL HELPERS
# ==========================================================

def quote_identifier(value: str) -> str:
    value = value.strip()

    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        raise ValueError(f"Invalid schema or table identifier: {value!r}")

    return f'"{value}"'


def quote_column(value: str) -> str:
    if not value or "\x00" in value:
        raise ValueError("Invalid column name.")

    return '"' + value.replace('"', '""') + '"'


def quote_literal(value: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError("Please select a valid brand.")

    return "'" + value.replace("'", "''") + "'"


def execute_dataframe(query: str) -> pd.DataFrame:
    result = get_query_executor().execute(query)

    if not isinstance(result, pd.DataFrame):
        raise TypeError("QueryExecutor.execute() must return a DataFrame.")

    return result


# ==========================================================
# DATASET HELPERS
# ==========================================================

def load_brands(schema_name: str, table_name: str) -> list[str]:
    table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"

    result = execute_dataframe(
        f"""
        SELECT DISTINCT brand__c AS brand
        FROM {table}
        WHERE brand__c IS NOT NULL
        ORDER BY brand
        """
    )

    if "brand" not in result.columns:
        raise ValueError("The brand query did not return a brand column.")

    return [str(value) for value in result["brand"].dropna().tolist()]


def load_table_metadata(
    schema_name: str,
    table_name: str,
    brand_name: str,
):
    executor = get_query_executor()
    extractor = SchemaExtractor(executor)

    table = f"{quote_identifier(schema_name)}.{quote_identifier(table_name)}"
    brand_literal = quote_literal(brand_name)

    metadata = extractor.get_columns(
        schema_name=schema_name,
        table_name=table_name,
    )

    if not isinstance(metadata, pd.DataFrame) or "column_name" not in metadata.columns:
        raise ValueError("Schema metadata must contain column_name.")

    sensitive = {str(column).casefold() for column in SENSITIVE_COLUMNS}

    safe_metadata = metadata.loc[
        ~metadata["column_name"].astype(str).str.casefold().isin(sensitive)
    ].copy()

    safe_columns = safe_metadata["column_name"].dropna().astype(str).tolist()

    if not safe_columns:
        raise ValueError("No privacy-approved columns are available.")

    projection = ", ".join(quote_column(column) for column in safe_columns)

    sample_df = execute_dataframe(
        f"""
        SELECT {projection}
        FROM {table}
        WHERE brand__c = {brand_literal}
        LIMIT 15000
        """
    )
    sample_df = remove_sensitive_columns(sample_df)

    count_df = execute_dataframe(
        f"""
        SELECT COUNT(*) AS row_count
        FROM {table}
        WHERE brand__c = {brand_literal}
        """
    )

    if count_df.empty or "row_count" not in count_df.columns:
        raise ValueError("Unable to retrieve the brand-specific row count.")

    row_count = int(count_df["row_count"].iloc[0])

    return safe_metadata, sample_df, row_count


def clear_chat():
    st.session_state.messages = []
    st.session_state.analytics_history = []
    st.session_state.last_analysis = None
    st.session_state.last_response = None
    st.session_state.generated_insight = None
    st.session_state.chat_orchestrator = None
    st.session_state.chat_orchestrator_scope = None


def markdown_answer(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "\n\n".join(f"- {item}" for item in value)

    return str(value)


# ==========================================================
# CHAT RESPONSE RENDERER
# ==========================================================

def render_chat_response(response: dict, message_id: str):
    if not isinstance(response, dict):
        st.error("Invalid response received.")
        return

    if not response.get("success", False):
        st.error(response.get("error") or "Analysis failed.")
        return

    if response.get("cache_hit"):
        st.caption("Served from exact Redis cache.")

    intent = response.get("intent")
    insight = response.get("insight") or {}

    if intent == "general":
        st.markdown(
            markdown_answer(insight.get("answer")) or "No response generated."
        )
        return

    if intent == "metadata":
        st.markdown("## 📊 Dataset Intelligence Report")

        answer = markdown_answer(insight.get("answer"))

        if answer:
            st.markdown("### 🧠 Key Insight")
            st.markdown(answer)

        sections = [
            ("📌 Executive Summary", "executive_summary"),
            ("💼 Business Value", "business_value"),
            ("📈 Important KPIs", "important_kpis"),
            ("🔍 Possible Analyses", "possible_analyses"),
            ("📊 Recommended Dashboards", "dashboard_recommendations"),
            ("🚀 Recommendations", "recommendations"),
        ]

        for title, key in sections:
            items = insight.get(key)

            if items:
                with st.expander(title):
                    st.markdown(markdown_answer(items))

        return

    if intent not in {"sql_query", "visualization"}:
        st.warning(f"Unsupported response intent: {intent}")
        return

    sql_text = response.get("sql")

    if sql_text:
        with st.expander("Generated SQL"):
            st.code(sql_text, language="sql")

    result_df = remove_sensitive_columns(
        pd.DataFrame(response.get("result") or [])
    )

    if result_df.empty:
        st.info(response.get("message") or "No matching records were found.")
        return

    if intent == "visualization":
        chart = response.get("chart")

        if not isinstance(chart, dict):
            st.error("No valid chart specification was returned.")
        else:
            try:
                fig = build_chart(result_df, chart)
                st.plotly_chart(
                    fig,
                    width="stretch",
                    key=f"chat_chart_{message_id}",
                )
            except Exception as ex:
                st.error(f"Unable to render visualization: {ex}")

    elif result_df.shape == (1, 1):
        value = result_df.iloc[0, 0]

        if pd.isna(value):
            display_value = "N/A"
        else:
            try:
                display_value = f"{float(value):,.2f}"
            except (TypeError, ValueError):
                display_value = str(value)

        st.metric(str(result_df.columns[0]), display_value)

    with st.expander("Query Results", expanded=intent == "sql_query"):
        st.dataframe(result_df, width="stretch", hide_index=True)

        st.download_button(
            "Download Results",
            data=result_df.to_csv(index=False),
            file_name="chat_analysis.csv",
            mime="text/csv",
            key=f"chat_download_{message_id}",
        )


# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.title("📊 AI Analytics Copilot")

menu = st.sidebar.radio(
    "Navigation",
    ["Data Overview", "Data Analysis", "Data Quality", "Chat Analytics"],
)

# menu = st.sidebar.selectbox(
#     "Navigation",
#     ["Data Overview", "Data Analysis", "Data Quality", "Chat Analytics"],
#     key="navigation_menu",
# )

st.sidebar.divider()
st.sidebar.subheader("Connect Redshift")

schema_input = st.sidebar.text_input("Schema", value="salesforce").strip()
table_input = st.sidebar.text_input("Table Name").strip()
input_scope = (schema_input, table_input)

# schema_col, table_col = st.sidebar.columns([1, 1.5])
# schema_input = schema_col.text_input("Schema",value="salesforce",).strip()
# table_input = table_col.text_input("Table",).strip()

input_scope = (schema_input, table_input)

# Invalidate fetched brands when the schema or table changes.
if (
    st.session_state.brands_scope is not None
    and st.session_state.brands_scope != input_scope
):
    st.session_state.brands = []
    st.session_state.selected_brand = None
    st.session_state.brands_scope = None
    st.session_state.pop("brand_selector", None)

if st.sidebar.button(
    "Fetch Brands",
    disabled=not schema_input or not table_input,
):
    try:
        with st.spinner("Fetching brands..."):
            brands = load_brands(schema_input, table_input)

        st.session_state.brands = brands
        st.session_state.brands_scope = input_scope
        st.session_state.selected_brand = None
        st.session_state.pop("brand_selector", None)

        if brands:
            st.sidebar.success(f"Found {len(brands)} brands.")
        else:
            st.sidebar.warning("No non-null brands were found.")

    except Exception as ex:
        st.session_state.brands = []
        st.session_state.brands_scope = None
        st.session_state.selected_brand = None
        st.sidebar.error(f"Unable to fetch brands: {ex}")

brands = st.session_state.brands

if brands:
    selected_brand = st.sidebar.selectbox(
        "Select Brand",
        options=brands,
        index=None,
        placeholder="Choose one brand",
        key="brand_selector",
    )
    st.session_state.selected_brand = selected_brand

can_load = (
    bool(st.session_state.selected_brand)
    and st.session_state.brands_scope == input_scope
)

if st.sidebar.button("Load Dataset", disabled=not can_load):
    try:
        brand = st.session_state.selected_brand

        with st.spinner("Loading brand-specific data..."):
            metadata_df, sample_df, row_count = load_table_metadata(
                schema_name=schema_input,
                table_name=table_input,
                brand_name=brand,
            )

        previous_scope = (
            st.session_state.schema_name,
            st.session_state.table_name,
            st.session_state.loaded_brand,
        )
        new_scope = (schema_input, table_input, brand)

        if previous_scope != new_scope:
            clear_chat()

        st.session_state.metadata_df = metadata_df
        st.session_state.sample_df = sample_df
        st.session_state.row_count = row_count
        st.session_state.schema_name = schema_input
        st.session_state.table_name = table_input
        st.session_state.loaded_brand = brand

        # Invalidate analysis only after a successful dataset load.
        st.session_state.dataset_version = uuid.uuid4().hex
        st.session_state.analysis_result = None
        st.session_state.analysis_version = None

        st.sidebar.success(f"Loaded: {brand}")

    except Exception as ex:
        st.sidebar.error(f"Dataset loading failed: {ex}")

if st.session_state.loaded_brand:
    st.sidebar.caption(f"Loaded brand: {st.session_state.loaded_brand}")

    selection_changed = (
        input_scope
        != (st.session_state.schema_name, st.session_state.table_name)
        or (
            st.session_state.selected_brand is not None
            and st.session_state.selected_brand != st.session_state.loaded_brand
        )
    )

    if selection_changed:
        st.sidebar.warning(
            "The selection differs from the loaded dataset. "
            "Existing pages still use the loaded dataset."
        )

if st.sidebar.button("Clear Chat"):
    clear_chat()
    st.rerun()


# ==========================================================
# LOADED DATA VALIDATION
# ==========================================================

df = st.session_state.sample_df

if not isinstance(df, pd.DataFrame):
    st.title("AI Analytics Copilot")
    st.info("Fetch brands, select one brand, and click Load Dataset.")
    st.stop()

if df.empty:
    st.title("AI Analytics Copilot")
    st.warning("The loaded brand has no sample records.")
    st.stop()

metadata_df = st.session_state.metadata_df

if not isinstance(metadata_df, pd.DataFrame):
    metadata_df = pd.DataFrame()

st.caption(
    f"Loaded scope: {st.session_state.schema_name}."
    f"{st.session_state.table_name} | Brand: {st.session_state.loaded_brand}"
)


# ==========================================================
# DATA OVERVIEW
# ==========================================================

if menu == "Data Overview":
    st.title("📊 Data Overview")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Brand Rows", f"{st.session_state.row_count:,}")
    c2.metric("Approved Columns", len(df.columns))
    c3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))

    categorical_count = sum(
        pd.api.types.is_object_dtype(dtype)
        or pd.api.types.is_string_dtype(dtype)
        or isinstance(dtype, pd.CategoricalDtype)
        for dtype in df.dtypes
    )
    c4.metric("Categorical Columns", categorical_count)

    st.caption(
        f"Profiling and local analysis use LIMIT of {len(df):,} rows. "
        "not a guaranteed representative sample."
    )

    st.subheader("Metadata")
    st.dataframe(metadata_df, width="stretch", hide_index=True)

    st.subheader("Sample Data")
    st.dataframe(df.head(100), width="stretch", hide_index=True)


# ==========================================================
# DATA ANALYSIS
# ==========================================================

elif menu == "Data Analysis":
    st.title("📈 Data Analysis")
    st.caption("Local statistics are based on the loaded sample.")

    if st.button("Refresh Analysis"):
        st.session_state.analysis_result = None
        st.session_state.analysis_version = None

    needs_analysis = (
        st.session_state.analysis_result is None
        or st.session_state.analysis_version != st.session_state.dataset_version
    )

    if needs_analysis:
        try:
            with st.spinner("Analyzing dataset..."):
                analysis = get_data_analyzer().analyze(
                    df=df.copy(),
                    total_rows=st.session_state.row_count,
                )

            if not isinstance(analysis, dict):
                raise TypeError("DataAnalysisOrchestrator must return a dictionary.")

            st.session_state.analysis_result = analysis
            st.session_state.analysis_version = st.session_state.dataset_version

        except Exception as ex:
            st.error(f"Data analysis failed: {ex}")
            st.stop()

    analysis = st.session_state.analysis_result

    tabs = st.tabs(
        [
            "📋 Profiling",
            "📌 Data Summary",
            "📊 KPIs",
            "📈 Segments",
            "📉 Trends",
            "🔗 Correlations",
            "🚨 Outliers",
            "🎯 Drivers",
        ]
    )

    with tabs[0]:
        render_profiling_tab(df)

    renderers = [
        ("summary", render_summary_tab),
        ("kpis", render_kpis_tab),
        ("segments", render_segment_tab),
        ("trends", render_trend_tab),
        ("correlations", render_correlation_tab),
        ("outliers", render_outlier_tab),
        # ("drivers", render_drivers_tab),
    ]

    for tab, (key, renderer) in zip(tabs[1:7], renderers):
        with tab:
            result = analysis.get(key)

            if key == "outliers" and result is None:
                result = analysis.get("anomalies")

            if not isinstance(result, dict):
                st.warning(f"No valid {key} analysis is available.")
            elif not result.get("success", False):
                st.warning(result.get("error") or f"{key.title()} analysis unavailable.")
            elif key == "segments":
                render_segment_tab(
                    result,
                    key_prefix=f"segments_{st.session_state.dataset_version}",
                )
            else:
                renderer(result)

    # Drivers uses the DataFrame and a user-selected target.
    with tabs[7]:
        render_drivers_tab(
            df=df,
            key_prefix=f"drivers_{st.session_state.dataset_version}",
        )

# ==========================================================
# DATA QUALITY
# ==========================================================

elif menu == "Data Quality":
    st.title("🔍 Data Quality")
    st.caption("Quality metrics apply to the loaded sample and approved columns.")

    missing_df = pd.DataFrame(
        {
            "Column": df.columns,
            "Missing": df.isna().sum().to_numpy(),
            "Missing %": df.isna().mean().mul(100).round(2).to_numpy(),
        }
    ).sort_values("Missing", ascending=False)

    st.subheader("Missing Values")
    st.dataframe(missing_df.head(50), width="stretch", hide_index=True)

    missing_plot = missing_df.loc[missing_df["Missing"] > 0].head(20)

    if not missing_plot.empty:
        fig = px.bar(
            missing_plot,
            x="Column",
            y="Missing",
            hover_data=["Missing %"],
            title="Top Missing Columns",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.success("No missing values were found in the loaded sample.")

    try:
        duplicate_rows = int(df.duplicated().sum())
        st.metric("Duplicate Sample Rows", duplicate_rows)
    except TypeError:
        st.warning("Duplicate detection is unavailable for nested column values.")


# ==========================================================
# CHAT ANALYTICS
# ==========================================================

elif menu == "Chat Analytics":
    st.title("🤖 Chat Analytics")
    st.info(f"Chat scope: {st.session_state.loaded_brand}")

    st.caption(
        "Examples: Average QA score; Explain this dataset; "
        "Plot monthly average QA score; "
        "Show average QA score by language as a bar chart."
    )

    # Store full assistant responses so charts and tables survive reruns.
    for message in st.session_state.messages[-20:]:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "response" in message:
                render_chat_response(message["response"], message["id"])
            else:
                st.markdown(markdown_answer(message.get("content")))

    question = st.chat_input("Ask a question about the loaded brand...")

    if question:
        user_message = {
            "id": uuid.uuid4().hex,
            "role": "user",
            "content": question,
        }
        st.session_state.messages.append(user_message)

        with st.chat_message("user"):
            st.markdown(question)

        started = time.perf_counter()

        try:
            with st.spinner("Analyzing..."):
                response = get_orchestrator().analyze_question(
                    question=question,
                    brand=st.session_state.loaded_brand,
                    schema_name=st.session_state.schema_name,
                    table_name=st.session_state.table_name,
                )

            if not isinstance(response, dict):
                raise TypeError("The orchestrator must return a dictionary.")

        except Exception as ex:
            response = {
                "success": False,
                "question": question,
                "error": f"Application error: {ex}",
            }

        print(f"Orchestrator Time: {time.perf_counter() - started:.2f}s")
        st.session_state.last_response = response

        if response.get("success") and response.get("intent") in {
            "sql_query",
            "visualization",
        }:
            st.session_state.last_analysis = {
                "question": response.get("question"),
                "metadata": response.get("metadata"),
                "sql": response.get("sql"),
                "result": response.get("result"),
                "chart": response.get("chart"),
            }

            st.session_state.analytics_history.append(
                st.session_state.last_analysis.copy()
            )
            st.session_state.analytics_history = (
                st.session_state.analytics_history[-20:]
            )

        assistant_message = {
            "id": uuid.uuid4().hex,
            "role": "assistant",
            "response": response,
        }
        st.session_state.messages.append(assistant_message)

        with st.chat_message("assistant"):
            render_chat_response(response, assistant_message["id"])
