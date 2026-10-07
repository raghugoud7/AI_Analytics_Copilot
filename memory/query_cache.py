# memory/query_cache.py

from datetime import datetime


class QueryCache:
    def __init__(self):
        self.cache = {}

    def get(self, question: str):
        return self.cache.get(question.lower().strip())

    def save(self, question: str, result: dict):
        self.cache[question.lower().strip()] = {
            "timestamp": datetime.now(),
            "result": result,
        }