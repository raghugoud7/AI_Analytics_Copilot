import hashlib
import json


def generate_cache_key(
    question: str,
    brand: str | None = None,
    schema_name: str | None = None,
    table_name: str | None = None,
) -> str:
    scope = {
        "version": 2,
        "question": question.strip(),
        "brand": brand,
        "schema_name": schema_name,
        "table_name": table_name,
    }
    payload = json.dumps(scope, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
