import copy
import uuid

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from vectorstore.embeddings import get_embeddings


class SemanticCache:

    def __init__(self):
        self.embeddings = get_embeddings()
        self.store = FAISS.from_texts(
            texts=["semantic-cache-initialization"],
            embedding=self.embeddings,
            metadatas=[{"is_initialization": True}],
        )
        self.responses = {}

    @staticmethod
    def _normalize(value: str | None) -> str:
        return " ".join((value or "").lower().strip().split())

    def _build_scope(
        self,
        question: str,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> str:
        return "\n".join(
            [
                f"Schema: {self._normalize(schema_name) or 'no_schema'}",
                f"Table: {self._normalize(table_name) or 'no_table'}",
                f"Brand: {self._normalize(brand) or 'no_brand'}",
                f"Question: {self._normalize(question)}",
            ]
        )

    def search(
        self,
        question: str,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
        threshold: float = 0.85,
    ) -> dict | None:
        scoped_question = self._build_scope(
            question=question,
            brand=brand,
            schema_name=schema_name,
            table_name=table_name,
        )

        results = self.store.similarity_search_with_relevance_scores(
            scoped_question,
            k=3,
        )

        requested_brand = self._normalize(brand)
        requested_schema = self._normalize(schema_name)
        requested_table = self._normalize(table_name)

        for document, similarity in results:
            metadata = document.metadata

            if metadata.get("is_initialization"):
                continue

            if metadata.get("brand") != requested_brand:
                continue

            if metadata.get("schema_name") != requested_schema:
                continue

            if metadata.get("table_name") != requested_table:
                continue

            response_id = metadata.get("response_id")

            print(f"Semantic Similarity: {similarity:.3f}")
            print(f"Semantic Brand: {requested_brand or 'no_brand'}")
            print(f"Semantic Table: {requested_table or 'no_table'}")

            if similarity >= threshold and response_id in self.responses:
                return copy.deepcopy(self.responses[response_id])

        return None

    def store_response(
        self,
        question: str,
        response: dict,
        brand: str | None = None,
        schema_name: str | None = None,
        table_name: str | None = None,
    ) -> None:
        response_id = str(uuid.uuid4())

        normalized_brand = self._normalize(brand)
        normalized_schema = self._normalize(schema_name)
        normalized_table = self._normalize(table_name)

        scoped_question = self._build_scope(
            question=question,
            brand=brand,
            schema_name=schema_name,
            table_name=table_name,
        )

        document = Document(
            page_content=scoped_question,
            metadata={
                "response_id": response_id,
                "brand": normalized_brand,
                "schema_name": normalized_schema,
                "table_name": normalized_table,
                "intent": response.get("intent", ""),
            },
        )

        self.store.add_documents([document])
        self.responses[response_id] = copy.deepcopy(response)

    def clear(self) -> None:
        self.store = FAISS.from_texts(
            texts=["semantic-cache-initialization"],
            embedding=self.embeddings,
            metadatas=[{"is_initialization": True}],
        )
        self.responses.clear()