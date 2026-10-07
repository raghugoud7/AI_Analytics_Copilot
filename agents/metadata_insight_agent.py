# agents/metadata_insight_agent.py

import json

from llm.llm_factory import get_llm

METADATA_INSIGHT_PROMPT = """
You are a Senior Analytics Consultant and BI Expert.

QUESTION:
{question}

DATASET METADATA:
{metadata}

Return ONLY JSON.

{{
  "answer": "",
  "executive_summary": [],
  "business_value": [],
  "important_kpis": [],
  "key_dimensions": [],
  "possible_analyses": [],
  "dashboard_recommendations": [],
  "recommendations": []
}}

Instructions:

- Think like a business consultant.
- Use bullet-point style content.
- Explain the dataset from a business perspective.
- Highlight KPIs and why they matter.
- Explain business decisions this data enables.
- Suggest useful dashboards.
- Suggest valuable analyses.
- Be insightful and executive-friendly.
- Avoid technical jargon.
- Keep answers concise but impactful.
"""


class MetadataInsightAgent:

    def __init__(self):

        self.llm = get_llm()

    def generate_insight(
        self,
        question: str,
        metadata: dict
    ):

        try:
            metadata_summary = {
                "tables": metadata.get(
                    "tables",
                    []
                ),
                "columns": metadata.get(
                    "columns",
                    []
                ),
                "measures": metadata.get(
                    "measures",
                    []
                ),
                "kpis": metadata.get(
                    "kpis",
                    []
                ),
                "dimensions": metadata.get(
                    "dimensions",
                    []
                ),
                "context": metadata.get(
                    "context",
                    ""
                )
            }

            prompt = METADATA_INSIGHT_PROMPT.format(
                question=question,
                metadata=json.dumps(
                    metadata_summary,
                    indent=2
                )
            )

            response = self.llm.invoke(
                prompt
            )

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
                    "key_findings": [],
                    "recommendations": []
                }

        except Exception as e:

            return {
                "answer": (
                    f"Unable to generate metadata insights: {str(e)}"
                ),
                "key_findings": [],
                "recommendations": []
            }