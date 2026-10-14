import json

from llm.llm_factory import get_llm
from prompts.visualization_prompt import VISUALIZATION_PROMPT


class VisualizationAgent:

    def __init__(self):
        self.llm = get_llm()

    def generate(self, question: str, metadata: dict, brand: str | None = None,) -> dict:
        if not brand:
            return {
                "success": False,
                "error": "No brand is currently loaded.",
            }

        prompt = VISUALIZATION_PROMPT.format(
            question=question,
            brand=brand.replace("'", "''"),
            metadata=json.dumps(metadata, indent=2, default=str),
        )

        response = self.llm.invoke(prompt)
        content = (
            response.content.replace("```json", "").replace("```", "").strip()
        )

        try:
            result = json.loads(content)
        except json.JSONDecodeError as ex:
            return {
                "success": False,
                "error": f"Invalid visualization response: {ex}",
                "raw_response": content,
            }

        if not result.get("sql"):
            return {
                "success": False,
                "error": "Visualization SQL was not generated.",
            }

        if not isinstance(result.get("chart"), dict):
            return {
                "success": False,
                "error": "Chart specification was not generated.",
            }

        return result