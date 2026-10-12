import uuid

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from vectorstore.embeddings import get_embeddings


class SemanticCache:
    def __init__(self):
        self.embeddings = get_embeddings()
        self.store = FAISS.from_texts(texts=["init"], embedding=self.embeddings)
        self.responses = {}

    def search(self, question: str, threshold: float = 0.85):
        results = self.store.similarity_search_with_score(question, k=1)

        if not results:
            return None

        doc, distance = results[0]
        similarity = 1 - distance

        print(f"Semantic Similarity: {similarity:.3f}")
        print(f"FAISS distance: {distance}")

        if similarity >= threshold:
            return self.responses.get(doc.metadata["response_id"])

        return None

    def store_response(self, question: str, response: dict):
        response_id = str(uuid.uuid4())
        doc = Document(
            page_content=question,
            metadata={"response_id": response_id},
        )

        self.store.add_documents([doc])
        self.responses[response_id] = response