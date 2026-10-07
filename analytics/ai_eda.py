# pages/ai_eda.py

import streamlit as st
import pandas as pd
import plotly.express as px

from services.redshift_service import RedshiftService
from services.llm_service import ask_llm
from prompts import AI_EDA_PROMPT


st.title("AI Powered Exploratory Data Analysis")

service = RedshiftService()

schema = st.session_state.get("schema")
table = st.session_state.get("table")

if not schema or not table:
    st.warning("Load metadata first")
    st.stop()

if st.button("Generate AI EDA"):

    with st.spinner("Loading metadata..."):

        metadata = service.load_metadata(
            schema,
            table
        )

        sample_data = service.get_sample_data(
            schema,
            table,
            limit=50000
        )

        row_count = service.get_row_count(
            schema,
            table
        )

    st.success("Data Loaded")

    # -------------------------
    # BASIC PROFILE
    # -------------------------

    st.header("Dataset Overview")

    c1, c2 = st.columns(2)

    with c1:
        st.metric(
            "Rows",
            f"{row_count:,}"
        )

    with c2:
        st.metric(
            "Columns",
            len(metadata)
        )

    st.dataframe(metadata)

    # -------------------------
    # NUMERIC ANALYSIS
    # -------------------------

    numeric_cols = sample_data.select_dtypes(
        include=["int64", "float64"]
    ).columns

    st.header("Numerical Analysis")

    if len(numeric_cols):

        st.dataframe(
            sample_data[numeric_cols]
            .describe()
            .transpose()
        )

    # -------------------------
    # CATEGORICAL ANALYSIS
    # -------------------------

    categorical_cols = sample_data.select_dtypes(
        include="object"
    ).columns

    st.header("Categorical Analysis")

    for col in categorical_cols[:10\]:

        tmp = (
            sample_data[col]
            .value_counts()
            .head(10)
            .reset_index()
        )

        fig = px.bar(
            tmp,
            x="index",
            y=col,
            title=f"Top Values : {col}"
        )

        st.plotly_chart(
            fig,
            use_container_width=True
        )

    # -------------------------
    # CORRELATION
    # -------------------------

    st.header("Correlation Analysis")

    if len(numeric_cols) > 1:

        corr = sample_data[
            numeric_cols
        ].corr()

        st.dataframe(corr)

    # -------------------------
    # AI INSIGHTS
    # -------------------------

    st.header("Executive Insights")

    metadata_context = metadata.to_string()

    sample_summary = (
        sample_data.describe(
            include="all"
        )
        .fillna("")
        .to_string()
    )

    prompt = AI_EDA_PROMPT.format(
        row_count=row_count,
        metadata=metadata_context,
        summary=sample_summary
    )

    insights = ask_llm(prompt)

    st.markdown(insights)