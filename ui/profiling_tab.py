import plotly.express as px
import streamlit as st


def render_profiling_tab(df):
    st.subheader("📋 Data Profiling")

    if df is None or not hasattr(df, "select_dtypes"):
        st.warning("No data available.")
        return

    numeric_df = df.select_dtypes(include="number")

    if len(numeric_df.columns) > 0:
        st.markdown("### Statistical Summary")

        st.dataframe(
            numeric_df.describe().T,
            width="stretch",
        )

        selected_col = st.selectbox(
            "Distribution Column",
            numeric_df.columns.tolist(),
            key="profile_distribution",
        )

        fig = px.histogram(
            df,
            x=selected_col,
            nbins=40,
            title=f"{selected_col} Distribution",
        )

        st.plotly_chart(fig, width="stretch")

    dtype_count = df.dtypes.astype(str).value_counts().reset_index()
    dtype_count.columns = ["Type", "Count"]

    st.markdown("### Data Types")

    fig = px.pie(
        dtype_count,
        names="Type",
        values="Count",
        title="Column Data Types",
    )

    st.plotly_chart(fig, width="stretch")