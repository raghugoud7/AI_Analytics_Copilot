# vectorstore/embeddings.py

import streamlit as st

from langchain_openai import OpenAIEmbeddings


def get_embeddings():

    return OpenAIEmbeddings(
        api_key=st.secrets["OPENAI_API_KEY"]
    )
