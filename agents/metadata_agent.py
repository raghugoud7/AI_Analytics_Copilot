# agents/metadata_agent.py

from cache.redis_service import RedisService
from utils.cache_utils import generate_cache_key
from vectorstore.faiss_manager import FAISSManager


class MetadataAgent:
    def __init__(self, enable_redis: bool = False):
        self.vector_store = FAISSManager()
        self.redis = RedisService() if enable_redis else None

    def _read_cache(self, cache_key: str) -> dict | None:
        if self.redis is None:
            return None

        try:
            cached = self.redis.get(cache_key)
            return cached if isinstance(cached, dict) else None
        except Exception as ex:
            print(f"Metadata Redis lookup skipped: {ex}")
            return None

    def _write_cache(self, cache_key: str, result: dict) -> None:
        if self.redis is None:
            return

        try:
            self.redis.set(cache_key, result, ttl=3600)
        except Exception as ex:
            print(f"Metadata Redis storage skipped: {ex}")

    @staticmethod
    def _safe_name(value) -> str:
        if value is None:
            return "Unknown"

        if isinstance(value, dict):
            return str(value.get("name") or "Unknown")

        return str(value)

    @staticmethod
    def _matches_scope(
        metadata: dict,
        schema_name: str | None,
        table_name: str | None,
    ) -> bool:
        document_schema = str(metadata.get("schema_name") or "").lower().strip()
        document_table = str(metadata.get("table_name") or "").lower().strip()
        expected_schema = (schema_name or "").lower().strip()
        expected_table = (table_name or "").lower().strip()

        if document_schema and expected_schema and document_schema != expected_schema:
            return False

        if document_table and expected_table and document_table != expected_table:
            return False

        return True

    def retrieve(
        self,
        question: str,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
        top_k: int = 25,
    ) -> dict:
        if not isinstance(question, str) or not question.strip():
            raise ValueError("A non-empty metadata question is required.")

        question = question.strip()
        top_k = max(1, min(int(top_k), 100))

        key_hash = generate_cache_key(
            question=question,
            brand=brand,
            schema_name=schema_name,
            table_name=table_name,
        )
        cache_key = f"metadata:v2:k{top_k}:{key_hash}"

        cached = self._read_cache(cache_key)

        if cached:
            print("METADATA REDIS CACHE HIT")
            return cached

        print(
            "METADATA REDIS CACHE MISS"
            if self.redis is not None
            else "Metadata Redis disabled; retrieving from FAISS."
        )

        docs = self.vector_store.search(question, k=top_k) or []

        scoped_docs = [
            doc
            for doc in docs
            if self._matches_scope(
                metadata=doc.metadata or {},
                schema_name=schema_name,
                table_name=table_name,
            )
        ]

        print("\n" + "=" * 80)
        print("METADATA RETRIEVAL")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Brand Scope: {brand or 'Not specified'}")
        print(f"Schema Scope: {schema_name or 'Not specified'}")
        print(f"Table Scope: {table_name or 'Not specified'}")
        print(f"Retrieved Documents: {len(docs)}")
        print(f"Scoped Documents: {len(scoped_docs)}")
        print("=" * 80)

        analysis_scope = {
            "brand": brand,
            "schema_name": schema_name,
            "table_name": table_name,
        }

        if not scoped_docs:
            result = {
                "documents": [],
                "columns": [],
                "kpis": [],
                "measures": [],
                "dimensions": [],
                "tables": [],
                "context": "",
                "analysis_scope": analysis_scope,
            }

            self._write_cache(cache_key, result)
            return result

        structured_docs = []
        columns = set()
        kpis = set()
        measures = set()
        dimensions = set()
        tables = set()
        context_parts = []

        for doc in scoped_docs:
            content = (doc.page_content or "").strip()
            metadata = doc.metadata or {}

            structured_docs.append({"content": content, "metadata": metadata})

            if content:
                context_parts.append(content)

            document_type = str(metadata.get("document_type") or "").lower().strip()
            name = self._safe_name(metadata.get("name"))

            document_schema = metadata.get("schema_name")
            document_table = metadata.get("table_name")

            if document_schema and document_table:
                tables.add(f"{document_schema}.{document_table}")

            detected_schema = None
            detected_table = None

            for line in content.splitlines():
                line = line.strip()

                if line.lower().startswith("schema:"):
                    detected_schema = line.split(":", 1)[1].strip()
                elif line.lower().startswith("table:"):
                    detected_table = line.split(":", 1)[1].strip()

            if detected_table:
                tables.add(
                    f"{detected_schema}.{detected_table}"
                    if detected_schema
                    else detected_table
                )

            if name == "Unknown":
                continue

            if document_type == "column":
                columns.add(name)
            elif document_type == "kpi":
                kpis.add(name)
            elif document_type == "measure":
                measures.add(name)
            elif document_type == "dimension":
                dimensions.add(name)
            elif document_type == "table":
                tables.add(name)

        scope_context = (
            "\n\nCurrent Analysis Scope:\n"
            f"- Brand: {brand or 'Not specified'}\n"
            f"- Schema: {schema_name or 'Not specified'}\n"
            f"- Table: {table_name or 'Not specified'}\n"
            "- Metadata describes dataset structure and business meaning.\n"
            "- Do not infer brand-specific KPI values from metadata alone."
        )

        result = {
            "documents": structured_docs,
            "columns": sorted(columns),
            "kpis": sorted(kpis),
            "measures": sorted(measures),
            "dimensions": sorted(dimensions),
            "tables": sorted(tables),
            "context": "\n\n".join(context_parts) + scope_context,
            "analysis_scope": analysis_scope,
        }

        print("\n" + "=" * 80)
        print("METADATA SUMMARY")
        print("=" * 80)
        print(f"Columns: {len(columns)}")
        print(f"KPIs: {len(kpis)}")
        print(f"Measures: {len(measures)}")
        print(f"Dimensions: {len(dimensions)}")
        print(f"Tables: {len(tables)}")
        print("=" * 80)

        self._write_cache(cache_key, result)
        return result
