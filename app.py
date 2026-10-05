import streamlit as st
import pandas as pd
import psycopg2
import plotly.express as px
import plotly.figure_factory as ff

from langchain_openai import ChatOpenAI
from prompts import (
    AI_EDA_PROMPT,
    CHAT_ANALYTICS_PROMPT
)

# =====================================================
# CONFIG
# =====================================================

st.set_page_config(
    page_title="AI Analytics Copilot",
    layout="wide",
    page_icon="📊"
)

# =====================================================
# GPT CONFIG
# =====================================================

llm = ChatOpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
    model="gpt-4o",
    temperature=0
)

# =====================================================
# REDSHIFT
# =====================================================

@st.cache_resource
def create_connection():

    conn = psycopg2.connect(
        host=st.secrets["REDSHIFT_HOST"],
        port=st.secrets["REDSHIFT_PORT"],
        dbname=st.secrets["REDSHIFT_DB"],
        user=st.secrets["REDSHIFT_USER"],
        password=st.secrets["REDSHIFT_PASSWORD"]
    )

    return conn


def run_query(query):

    conn = create_connection()

    try:
        return pd.read_sql(query, conn)

    except Exception:
        conn.rollback()
        raise


# =====================================================
# AI INSIGHTS
# =====================================================

def generate_ai_insights():

    prompt = AI_EDA_PROMPT.format(
        row_count=st.session_state.total_rows,
        metadata=metadata.to_string(),
        summary=df.describe(include="all").to_string()
    )

    response = llm.invoke(prompt)

    return response.content

# =====================================================
# SESSION
# =====================================================

if "metadata" not in st.session_state:
    st.session_state.metadata = None

if "sample_data" not in st.session_state:
    st.session_state.sample_data = None

if "table" not in st.session_state:
    st.session_state.table = None

if "schema" not in st.session_state:
    st.session_state.schema = None

# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("📊 AI Analytics Copilot")

menu = st.sidebar.radio(
    "Navigation",
    [
        "Data Overview",
        "EDA Dashboard",
        "Data Quality",
        "AI Insights",
        "Chat Analytics"
    ]
)

# =====================================================
# DATA LOAD SECTION
# =====================================================

with st.sidebar:

    st.markdown("---")

    st.subheader("Connect Redshift")

    schema = st.text_input(
        "Schema",
        value="salesforce"
    )

    table = st.text_input(
        "Table Name"
    )

    if st.button("Load Dataset"):

        try:

            metadata_query = f"""
            SELECT
                column_name,
                data_type
            FROM information_schema.columns
            WHERE table_schema='{schema}'
            AND table_name='{table}'
            ORDER BY ordinal_position
            """

            metadata = run_query(metadata_query)

            sample_query = f"""
            SELECT *
            FROM {schema}.{table}
            LIMIT 5000
            """

            sample_df = run_query(sample_query)

            count_query = f"""
            SELECT COUNT(*) total_rows
            FROM {schema}.{table}
            """

            count_df = run_query(count_query)

            st.session_state.metadata = metadata
            st.session_state.sample_data = sample_df
            st.session_state.total_rows = int(
                count_df.iloc[0]["total_rows"]
            )

            st.session_state.schema = schema
            st.session_state.table = table

            st.success("Dataset Loaded")

        except Exception as e:

            st.error(str(e))

# =====================================================
# VALIDATION
# =====================================================

if st.session_state.sample_data is None:

    st.title("AI Analytics Copilot")

    st.info(
        "Load Redshift table from left menu"
    )

    st.stop()

df = st.session_state.sample_data
metadata = st.session_state.metadata

# =====================================================
# PAGE 1
# =====================================================

if menu == "Data Overview":

    st.title("📊 Data Overview")

    rows = st.session_state.total_rows
    cols = len(df.columns)

    numeric_cols = len(
        df.select_dtypes(include="number").columns
    )

    categorical_cols = len(
        df.select_dtypes(
            include=["object"]
        ).columns
    )

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("Rows", f"{rows:,}")
    c2.metric("Columns", cols)
    c3.metric("Numeric", numeric_cols)
    c4.metric("Categorical", categorical_cols)

    st.markdown("### Metadata")

    st.dataframe(
        metadata,
        use_container_width=True
    )

    st.markdown("### Sample Data")

    st.dataframe(
        df.head(100),
        use_container_width=True
    )

# =====================================================
# PAGE 2
# =====================================================

elif menu == "EDA Dashboard":

    st.title("📈 EDA Dashboard")

    numeric_df = df.select_dtypes(
        include="number"
    )

    if len(numeric_df.columns) > 0:

        st.subheader("Statistics")

        st.dataframe(
            numeric_df.describe().T,
            use_container_width=True
        )

        selected_column = st.selectbox(
            "Distribution",
            numeric_df.columns
        )

        fig = px.histogram(
            df,
            x=selected_column,
            title=selected_column
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    dtype_count = (
        df.dtypes.astype(str)
        .value_counts()
    )

    fig = px.pie(
        values=dtype_count.values,
        names=dtype_count.index,
        title="Column Types"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

# =====================================================
# PAGE 3
# =====================================================

elif menu == "Data Quality":

    st.title("🔍 Data Quality")

    missing = df.isnull().sum()

    missing_df = pd.DataFrame(
        {
            "Column": missing.index,
            "Missing": missing.values
        }
    )

    missing_df = missing_df.sort_values(
        "Missing",
        ascending=False
    )

    st.subheader("Missing Values")

    st.dataframe(
        missing_df.head(30)
    )

    fig = px.bar(
        missing_df.head(20),
        x="Column",
        y="Missing",
        title="Top Missing Columns"
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )

    duplicate_count = df.duplicated().sum()

    st.metric(
        "Duplicate Rows",
        duplicate_count
    )

# =====================================================
# PAGE 4
# =====================================================

elif menu == "AI Insights":

    st.title("🤖 AI Insights")

    if st.button("Generate Insights"):

        profile = f"""
Rows: {st.session_state.total_rows}

Columns:
{list(df.columns)}

Data Types:
{metadata.to_string()}

Summary:
{df.describe(include="all").to_string()}
"""

        with st.spinner(
            "Generating insights..."
        ):

            insights = generate_ai_insights()

        st.markdown(insights)

# =====================================================
# PAGE 5
# =====================================================

elif menu == "Chat Analytics":

    st.title("💬 Chat Analytics")

    question = st.chat_input(
        "Ask a business question..."
    )

    if question:

        with st.chat_message("user"):
            st.write(question)

        context = f"""
            Dataset Columns:
            {list(df.columns)}

            Metadata:
            {metadata.to_string()}

            Summary:
            {df.describe(include='all').to_string()}
            """
        
        prompt = f"""
            {CHAT_ANALYTICS_PROMPT}

            DATASET CONTEXT

            {context}

            QUESTION

            {question}
            """

        with st.spinner("Analyzing..."):
            response = llm.invoke(prompt)
        with st.chat_message("assistant"):
            st.markdown(
                response.content
            )