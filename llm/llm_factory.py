import os
import streamlit as st

from langchain_openai import ChatOpenAI


def get_api_key():

    try:
        return st.secrets["OPENAI_API_KEY"]
    except Exception:
        return os.getenv("OPENAI_API_KEY")


def get_llm():
    return ChatOpenAI(
        api_key=get_api_key(),
        model="gpt-5",
        temperature=0
    )
