import hashlib
import re


STOP_WORDS = {
    "what",
    "is",
    "the",
    "show",
    "give",
    "me",
    "please",
}


def normalize_text(value: str | None) -> str:
    value = re.sub(r"[^\w\s]", "", (value or "").lower().strip())
    return " ".join(word for word in value.split() if word not in STOP_WORDS)


def generate_cache_key(question: str, brand: str | None = None) -> str:
    normalized_question = normalize_text(question)
    normalized_brand = normalize_text(brand) or "no_brand"
    cache_scope = f"brand:{normalized_brand}|question:{normalized_question}"

    return hashlib.sha256(cache_scope.encode("utf-8")).hexdigest()