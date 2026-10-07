# agents/metadata_agent.py

from vectorstore.faiss_manager import FAISSManager
from cache.redis_service import RedisService

class MetadataAgent:

    def __init__(self):
        self.vector_store = FAISSManager()
        self.redis = RedisService()

    def _safe_name(self, value) -> str:
        if value is None:
            return "Unknown"

        if isinstance(value, dict):
            return value.get("name", "Unknown")

        return str(value)

    def retrieve(self, question: str, top_k: int = 25):
        
        cache_key = f"metadata:{question}"
        cached = self.redis.get(cache_key)

        if cached:
            return cached
        
        docs = self.vector_store.search(question, k=top_k)

        print("\n" + "=" * 80)
        print("METADATA RETRIEVAL")
        print("=" * 80)
        print(f"Question: {question}")
        print(f"Retrieved Documents: {len(docs)}")
        print("=" * 80)

        if not docs:
            return {
                "documents": [],
                "columns": [],
                "kpis": [],
                "measures": [],
                "dimensions": [],
                "tables": [],
                "context": "",
            }

        structured_docs = []
        columns = set()
        kpis = set()
        measures = set()
        dimensions = set()
        tables = set()
        context_parts = []

        for doc in docs:
            content = doc.page_content.strip()
            metadata = doc.metadata if doc.metadata else {}

            structured_docs.append(
                {"content": content, "metadata": metadata}
            )

            if content:
                context_parts.append(content)

            document_type = str(
                metadata.get("document_type", "")
            ).lower().strip()

            name = self._safe_name(metadata.get("name"))

            # Parse table information

            schema_name = metadata.get("schema_name")
            table_name = metadata.get("table_name")

            if schema_name and table_name:
                tables.add(f"{schema_name}.{table_name}")

            if content:
                detected_schema = None
                detected_table = None

                for line in content.splitlines():
                    line = line.strip()

                    if line.lower().startswith("schema:"):
                        detected_schema = line.split(":", 1)[1].strip()

                    elif line.lower().startswith("table:"):
                        detected_table = line.split(":", 1)[1].strip()

                if detected_table:
                    if detected_schema:
                        tables.add(f"{detected_schema}.{detected_table}")
                    else:
                        tables.add(detected_table)

            # Collect semantic groups

            if document_type == "column":
                if name != "Unknown":
                    columns.add(name)

            elif document_type == "kpi":
                if name != "Unknown":
                    kpis.add(name)

            elif document_type == "measure":
                if name != "Unknown":
                    measures.add(name)

            elif document_type == "dimension":
                if name != "Unknown":
                    dimensions.add(name)

            elif document_type == "table":
                if name != "Unknown":
                    tables.add(name)

        print("\n" + "=" * 80)
        print("METADATA SUMMARY")
        print("=" * 80)
        print(f"Columns: {len(columns)}")
        print(f"KPIs: {len(kpis)}")
        print(f"Measures: {len(measures)}")
        print(f"Dimensions: {len(dimensions)}")
        print(f"Tables: {len(tables)}")
        print("=" * 80)

        result = {
            "documents": structured_docs,
            "columns": sorted(list(columns)),
            "kpis": sorted(list(kpis)),
            "measures": sorted(list(measures)),
            "dimensions": sorted(list(dimensions)),
            "tables": sorted(list(tables)),
            "context": "\n\n".join(context_parts),
        }
        
        self.redis.set(cache_key, result, ttl=3600)
        return result