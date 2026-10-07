import json
import pandas as pd

from langchain_openai import ChatOpenAI

import streamlit as st
from llm.llm_factory import get_llm
from prompts.insight_prompt import (
    INSIGHT_PROMPT
)


class InsightAgent:

    def __init__(self):

        self.llm = get_llm()

    def generate_insight(
        self,
        question: str,
        metadata: str,
        sql: str,
        result: pd.DataFrame,
        history=None
    ):
        if history is None:
            history = []
            
        if result.empty:
            return {
                "answer": "No records returned.",
                "evidence": [],
                "key_metrics": {},
                "observations": [],
                "risks": [],
                "opportunities": [],
                "recommendations": [],
                "confidence_level": "low"
            }

        result_summary = {
            "rows": len(result),
            "columns": list(result.columns),
            "sample_data": (
                result.head(100)
                .to_dict("records")
            )
        }

        prompt = INSIGHT_PROMPT.format(
            question=question,
            metadata=metadata,
            sql=sql,
            results=json.dumps(
                result_summary,
                indent=2,
                default=str
            ),
            history=json.dumps(
                history,
                indent=2,
                default=str
            )
        )

        response = self.llm.invoke(prompt)

        content = (
            response.content
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

        try:

            return json.loads(content)

        except Exception:

            return {
                "answer": content,
                "evidence": [],
                "key_metrics": {},
                "observations": [],
                "risks": [],
                "opportunities": [],
                "recommendations": [],
                "confidence_level": "unknown"
            }