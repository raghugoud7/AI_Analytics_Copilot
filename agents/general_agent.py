from llm.llm_factory import get_llm

GENERAL_PROMPT = """
You are an AI Analytics Copilot.

Answer naturally and professionally.

Question:

{question}
"""


class GeneralAgent:

    def __init__(self):
        self.llm = get_llm()

    def respond(
        self,
        question: str):
        prompt = GENERAL_PROMPT.format(
            question=question
        )

        response = self.llm.invoke(
            prompt
        )

        answer = (
            response.content.strip()
            if response.content
            else "Unable to generate response."
            )
        
        return {
            "answer": answer
        }