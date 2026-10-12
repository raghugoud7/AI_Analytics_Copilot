# app.py

import streamlit as st
import pandas as pd
import plotly.express as px
import time

from database.query_executor import QueryExecutor
from database.schema_extractor import SchemaExtractor

from agents.orchestrator import (
    AnalyticsOrchestrator
)

from config.privacy import SENSITIVE_COLUMNS
from utils.privacy import remove_sensitive_columns
from analytics.data_analysis_orchestrator import DataAnalysisOrchestrator

from ui.profiling_tab import render_profiling_tab
from ui.summary_tab import render_summary_tab
from ui.segment_tab import render_segment_tab
from ui.kpis_tab import render_kpis_tab
from ui.trend_tab import render_trend_tab
from ui.correlation_tab import render_correlation_tab
from ui.outliers_tab import render_outlier_tab
from ui.drivers_tab import render_drivers_tab

# ==========================================================
# PAGE CONFIG
# ==========================================================

st.set_page_config(
    page_title="AI Analytics Copilot",
    page_icon="📊",
    layout="wide"
)

# ==========================================================
# SESSION STATE
# ==========================================================

if "metadata_df" not in st.session_state:
    st.session_state.metadata_df = None

if "sample_df" not in st.session_state:
    st.session_state.sample_df = None

if "row_count" not in st.session_state:
    st.session_state.row_count = 0

if "schema_name" not in st.session_state:
    st.session_state.schema_name = None

if "table_name" not in st.session_state:
    st.session_state.table_name = None
    
if "messages" not in st.session_state:
    st.session_state.messages = []
    
if "analytics_history" not in st.session_state:
    st.session_state.analytics_history = []
    
if "last_analysis" not in st.session_state:
    st.session_state.last_analysis = None

if "last_response" not in st.session_state:
    st.session_state.last_response = None

if "generated_insight" not in st.session_state:
    st.session_state.generated_insight = None
    
if "brands" not in st.session_state:
    st.session_state.brands = []

if "selected_brand" not in st.session_state:
    st.session_state.selected_brand = None

if "loaded_brand" not in st.session_state:
    st.session_state.loaded_brand = None

if "brand_table" not in st.session_state:
    st.session_state.brand_table = None

# ==========================================================
# CACHE
# ==========================================================

@st.cache_resource
def get_query_executor():
    return QueryExecutor()

@st.cache_resource
def get_orchestrator():
    return AnalyticsOrchestrator()

@st.cache_resource
def get_data_analyzer():
    return DataAnalysisOrchestrator()


# ==========================================================
# HELPERS
# ==========================================================

def load_table_metadata(
    schema_name,
    table_name,
    brand_name,
):

    query_executor = get_query_executor()
    schema_extractor = SchemaExtractor(query_executor)

    metadata = schema_extractor.get_columns(
        schema_name=schema_name,
        table_name=table_name
    )

    row_count = schema_extractor.get_table_stats(
        schema_name=schema_name,
        table_name=table_name,
        brand_name=brand_name
    )

    sample_query = f"""
    SELECT *
    FROM {schema_name}.{table_name}
    WHERE brand__c = '{brand_name}'
    LIMIT 5000
    """

    sample_df = query_executor.execute(sample_query)
    sample_df = remove_sensitive_columns(sample_df)
    
    return (
        metadata,
        sample_df,
        row_count
    )

def load_brands(
    schema_name,
    table_name,
):
    query_executor = get_query_executor()

    query = f"""
    SELECT DISTINCT brand__c
    FROM {schema_name}.{table_name}
    WHERE brand__c IS NOT NULL
    ORDER BY brand__c
    """
    
    result = query_executor.execute(query)
    
    if isinstance(result, pd.DataFrame):

        if "brand__c" not in result.columns:
            return []

        return (
            result["brand__c"]
            .dropna()
            .astype(str)
            .tolist()
        )

    return []

# ==========================================================
# SIDEBAR
# ==========================================================

st.sidebar.title("📊 AI Analytics Copilot")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Data Overview",
        "Data Analysis",
        "Data Quality",
        "Chat Analytics"
    ]
)

st.sidebar.markdown("---")
st.sidebar.subheader("Connect Redshift")

schema_name = st.sidebar.text_input("Schema", value="salesforce")
table_name = st.sidebar.text_input("Table Name")


# ----------------------------------
# Load Brands
# ----------------------------------

if st.sidebar.button("Fetch Brands"):
    
    try:
        st.session_state.brands = load_brands(
            schema_name,
            table_name,
        )

        st.session_state.brand_table = (table_name)

        st.sidebar.success(
            f"Loaded {len(st.session_state.brands)} brands"
        )

    except Exception as ex:

        st.session_state.brands = []
        st.sidebar.error(
            f"Unable to load brands: {ex}"
        )
    
# ----------------------------------
# Brand Dropdown
# ----------------------------------

brands = st.session_state.get("brands",[],)

if brands:

    selected_brand = st.sidebar.selectbox(
        "Brand",
        brands,
    )

    st.session_state.selected_brand = (
        selected_brand
    )

# ----------------------------------
# Load Dataset
# ----------------------------------

if st.sidebar.button("Load Dataset"):
    try:
        with st.spinner("Loading Metadata..."):
            metadata_df, sample_df, row_count = load_table_metadata(
                schema_name,
                table_name,
                st.session_state.selected_brand,
            )

            st.session_state.metadata_df = metadata_df
            st.session_state.sample_df = sample_df
            st.session_state.row_count = row_count
            st.session_state.schema_name = schema_name
            st.session_state.table_name = table_name
            st.session_state.loaded_brand = (
                st.session_state.selected_brand
            )

        st.sidebar.success("Dataset Loaded")
    
    except Exception as e:
        st.sidebar.error(str(e))
        
    # if st.session_state.loaded_brand:
    #     st.caption(
    #         f"🏫 Brand: {st.session_state.loaded_brand}"
    #     )
        
if st.sidebar.button("Clear Chat"):

    st.session_state.messages = []
    st.session_state.analytics_history = []
    st.session_state.last_analysis = None
    st.session_state.last_response = None
    st.session_state.generated_insight = None
    st.rerun()
    

# ==========================================================
# VALIDATION
# ==========================================================

if st.session_state.sample_df is None:
    st.title("AI Analytics Copilot")
    st.info("Load a Redshift table from the left menu.")
    st.stop()

# ==========================================================
# DATA
# ==========================================================

metadata_df = st.session_state.metadata_df
if metadata_df is None:
    metadata_df = pd.DataFrame()

df = st.session_state.sample_df

if st.session_state.selected_brand:
    st.caption(
        f"🏫 Brand: "
        f"{st.session_state.selected_brand}"
    )
    
if df is None:
    df = pd.DataFrame()

if df.empty:
    st.title("AI Analytics Copilot")
    st.warning(
        "No data is currently loaded. Please load a Redshift table from the left menu."
    )
    st.stop()

# ==========================================================
# DATA OVERVIEW
# ==========================================================

if menu == "Data Overview":
    st.title("📊 Data Overview")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Rows", f"{st.session_state.row_count:,}")
    c2.metric("Columns", len(df.columns))
    c3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))
    c4.metric(
        "Categorical Columns",
        len(df.select_dtypes(include=["object", "string"]).columns),
    )

    st.markdown("### Metadata")
    st.dataframe(metadata_df, width="stretch")

    st.markdown("### Sample Data")
    st.dataframe(df.head(100), width="stretch")

# ==========================================================
# EDA
# ==========================================================

elif menu == "Data Analysis":
    st.title("📈 Data Analysis")
    
    analyzer = get_data_analyzer()

    with st.spinner(
        "Analyzing dataset..."
    ):
        analysis = analyzer.analyze(
            df=df,
            total_rows=st.session_state.row_count,
        )


        tabs = st.tabs(
            [
                "📋 Profiling",
                "📌 Executive Summary",
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
    
    with tabs[1]:
        render_summary_tab(analysis["summary"])
        
    with tabs[2]:
        render_kpis_tab(analysis["kpis"])
    
    with tabs[3]:
        render_segment_tab(analysis["segments"])
    
    with tabs[4]:
        render_trend_tab(analysis["trends"])

    with tabs[5]:
        render_correlation_tab(analysis["correlations"])
        
    with tabs[6]:
        render_outlier_tab(analysis["outliers"])
        
    with tabs[7]:
        render_drivers_tab(analysis["drivers"])

# ==========================================================
# DATA QUALITY
# ==========================================================

elif menu == "Data Quality":
    st.title("🔍 Data Quality")

    missing = df.isnull().sum().sort_values(ascending=False)
    missing_df = pd.DataFrame({"Column": missing.index, "Missing": missing.values})

    st.subheader("Missing Values")
    st.dataframe(missing_df.head(50), width="stretch")

    fig = px.bar(
        missing_df.head(20),
        x="Column",
        y="Missing",
        title="Top Missing Columns",
    )
    st.plotly_chart(fig, width="stretch")

    duplicate_rows = 0
    if df is not None and hasattr(df, "duplicated"):
        duplicate_rows = int(df.duplicated().sum())
    st.metric("Duplicate Rows", duplicate_rows)

# ==========================================================
# CHAT ANALYTICS
# ==========================================================

elif menu == "Chat Analytics":
    st.title("🤖 Chat Analytics")
    
    if st.session_state.loaded_brand:
        st.info(
            f"🏫 Chat Analytics Scope: "
            f"{st.session_state.loaded_brand}"
        )
        
    st.info(
        """
        Ask general, metadata, or analytics questions.

        Examples:

        • Hi
        • What can you do?
        • What KPIs are available?
        • Explain this dataset
        • Top 10 agents by quality score
        • Average QA score
        """
    )

    MAX_MESSAGES = 20
    messages = st.session_state.messages[-MAX_MESSAGES:]
    
    # for message in st.session_state.messages:
    
    for message in messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Ask a question...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})

        with st.chat_message("user"):
            st.write(question)

        try:
            orchestrator = get_orchestrator()
            start = time.time()
            with st.spinner("Analyzing..."):
                response = orchestrator.analyze_question(
                    question= question,
                    brand=st.session_state.loaded_brand
                    )

            print(
            f"✅ Orchestrator Time: "
            f"{time.time() - start:.2f}s"
            )
            print("\nFULL RESPONSE")
            print(response)

            if response.get("cache_hit"):
                st.success("⚡ Served from Redis Cache")

            if response.get("semantic_cache_hit"):
                st.success("🧠 Served from Semantic Cache")
                
            st.session_state.last_response = response

            if response.get("success") and response.get("intent") == "sql_query":
                st.session_state.last_analysis = {
                    "question": response.get("question"),
                    "metadata": response.get("metadata"),
                    "sql": response.get("sql"),
                    "result": response.get("result"),
                }

                st.session_state.analytics_history.append(
                    {
                        "question": response.get("question"),
                        "sql": response.get("sql"),
                        "result": response.get("result"),
                    }
                )

            if not response.get("success", False):
                error_message = response.get("error", "Unknown Error")

                st.session_state.messages.append(
                    {"role": "assistant", "content": error_message}
                )

                with st.chat_message("assistant"):
                    st.error(error_message)

            else:
                intent = response.get("intent", "")

                with st.chat_message("assistant"):
                    if intent == "general":
                        insight = response.get("insight") or {}
                        answer = insight.get("answer", "No response generated.")

                        st.write(answer)

                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer}
                        )

                    elif intent == "metadata":
                        insight = response.get("insight") or {}
                        st.markdown("## 📊 Dataset Intelligence Report")
                        answer = insight.get("answer", "")
                        if answer:
                            st.markdown("### 🧠 Key Insight")
                            if isinstance(answer, list):
                                for item in answer:
                                    st.markdown(
                                        f"""
                                        ✅ {item}
                                        """
                                    )
                            else:
                                st.success(answer)

                        sections = [
                            ("📌 Executive Summary", "executive_summary", "✅"),
                            ("💼 Business Value", "business_value", "💡"),
                            ("📈 Important KPIs", "important_kpis", "📊"),
                            ("🔍 Possible Analyses", "possible_analyses", "🔎"),
                            ("📊 Recommended Dashboards", "dashboard_recommendations", "📈"),
                            ("🚀 Recommendations", "recommendations", "⚠️"),
                        ]

                        for title, key, icon in sections:
                            items = insight.get(key, [])
                            if items:
                                with st.expander(title, expanded=False):
                                    for item in items:
                                        st.markdown(f"{icon} {item}")

                        st.session_state.messages.append(
                            {"role": "assistant", "content": answer}
                        )

                    elif intent == "sql_query":
                        print("✅ SQL UI RENDER START")
                        # st.caption("Intent: SQL Query")

                        sql_text = response.get("sql", "")
                        
                        if sql_text:
                            with st.expander("Generated SQL"):
                                st.code(sql_text, language="sql")

                        result = response.get("result")

                        if result:
                            df = pd.DataFrame(result)
                            df = df.drop(columns=list(SENSITIVE_COLUMNS), errors="ignore")
                            print(f"✅ DataFrame Shape: "f"{df.shape}")

                            if len(df) == 1 and len(df.columns) == 1:
                                raw_value = df.iloc[0, 0]

                                try:
                                    metric_value = round(float(raw_value), 2)
                                except Exception:
                                    metric_value = raw_value

                                st.metric(label=df.columns[0], value=metric_value)
                                
                            print("✅ Rendering DataFrame")

                            with st.expander("Query Results"):
                                st.dataframe(df, width="stretch")
                                
                            print("✅ DataFrame Rendered")

                    # if response.get("insight_available", False):
                    #     if st.button("Generate Insight", key=f"insight_{question}"):
                    #         analysis = st.session_state.get("last_analysis")

                    #         if not analysis:
                    #             st.error("No analysis available.")
                    #         else:
                    #             with st.spinner("Generating Insight..."):
                    #                 insight = orchestrator.generate_insight(
                    #                     question=analysis["question"],
                    #                     sql=analysis["sql"],
                    #                     result=analysis["result"],
                    #                     metadata=analysis["metadata"]["context"],
                    #                     history=st.session_state.analytics_history,
                    #                 )

                    #                 st.session_state["generated_insight"] = insight

                    # generated_insight = st.session_state.get("generated_insight")

                    # if generated_insight:
                    #     st.markdown("### AI Insight")
                    #     st.write(
                    #         generated_insight.get(
                    #             "answer", "No insight generated."
                    #         )
                    #     )

                    #     observations = generated_insight.get("observations", [])
                    #     if observations:
                    #         st.markdown("#### Key Observations")
                    #         for item in observations:
                    #             st.write(f"• {item}")

                    #     recommendations = generated_insight.get(
                    #         "recommendations", []
                    #     )
                    #     if recommendations:
                    #         st.markdown("#### Recommendations")
                    #         for item in recommendations:
                    #             st.write(f"• {item}")

        except Exception as ex:
            error_message = f"Application Error: {str(ex)}"

            st.session_state.messages.append(
                {"role": "assistant", "content": error_message}
            )

            with st.chat_message("assistant"):
                st.error(error_message)