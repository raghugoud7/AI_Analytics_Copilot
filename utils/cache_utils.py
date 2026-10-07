import hashlib


def generate_cache_key(question: str) -> str:
    normalized = " ".join(question.lower().strip().split())
    return hashlib.md5(normalized.encode()).hexdigest()