# memory/chat_memory.py

class ChatMemory:

    def __init__(self):

        self.history = []

    def add(
        self,
        question,
        sql,
        result,
        insight
    ):

        self.history.append({
            "question": question,
            "sql": sql,
            "result": result,
            "insight": insight
        })

    def get_context(
        self,
        limit=5
    ):

        return self.history[-limit:]