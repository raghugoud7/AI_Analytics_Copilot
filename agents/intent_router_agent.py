import json

from typing import Dict, Any

from llm.llm_factory import get_llm

from prompts.intent_prompt import (
    INTENT_PROMPT
)


class IntentRouterAgent:

    def __init__(self):

        self.llm = get_llm()

    def classify(
        self,
        question: str
    ) -> Dict[str, Any]:

        try:

            prompt = (
                INTENT_PROMPT.format(
                    question=question
                )
            )

            response = (
                self.llm.invoke(
                    prompt
                )
            )

            print("\n" + "=" * 80)
            print("RAW INTENT RESPONSE")
            print("=" * 80)
            print(response.content)
            print("=" * 80)

            content = (
                response.content
                .replace(
                    "```json",
                    ""
                )
                .replace(
                    "```",
                    ""
                )
                .strip()
            )

            result = json.loads(
                content
            )

            return {
                "intent":
                result.get(
                    "intent",
                    "sql_query"
                )
            }

        except Exception as ex:

            print("\n" + "=" * 80)
            print("INTENT ROUTER ERROR")
            print("=" * 80)
            print(str(ex))
            print("=" * 80)

            return {
                "intent": "sql_query"
            }