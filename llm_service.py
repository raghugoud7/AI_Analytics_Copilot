import streamlit as st

from langchain_openai import ChatOpenAI

from prompts import SYSTEM_PROMPT


llm = ChatOpenAI(
    api_key=st.secrets["OPENAI_API_KEY"],
    model="gpt-4o",
    temperature=0
)


def generate_answer(question, metadata):

    prompt = f"""
{SYSTEM_PROMPT}

DATA CONTEXT

{metadata}

QUESTION

{question}
"""

    response = llm.invoke(prompt)

    return response.content