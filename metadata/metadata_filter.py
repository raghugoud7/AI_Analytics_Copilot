class MetadataFilter:

    def apply(self, metadata: dict) -> dict:
        return {
            "tables": metadata.get("tables", []),
            "kpis": metadata.get("kpis", [])[:5],
            "measures": metadata.get("measures", [])[:10],
            "dimensions": metadata.get("dimensions", [])[:10],
            "columns": metadata.get("columns", [])[:20],
            "context": metadata.get("context", "")[:3000],
        }