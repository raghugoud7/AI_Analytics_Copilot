# vectorstore/faiss_manager.py

from langchain_community.vectorstores import FAISS

from vectorstore.embeddings import (
    get_embeddings
)


class FAISSManager:

    def __init__(
        self,
        index_path="vectorstore/index"
    ):

        self.embeddings = (
            get_embeddings()
        )

        self.vectorstore = (
            FAISS.load_local(
                index_path,
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        )

    def search(
        self,
        query,
        k=25
    ):

        docs = (
            self.vectorstore.similarity_search(
                query,
                k=k
            )
        )

        print("\n" + "=" * 80)
        print("FAISS QUERY")
        print("=" * 80)
        print(query)

        print("\n" + "=" * 80)
        print("FAISS RESULTS")
        print("=" * 80)

        for index, doc in enumerate(
            docs,
            start=1
        ):

            print(
                f"\nResult {index}"
            )

            print("-" * 80)

            print(
                doc.page_content
            )

        print("=" * 80)

        return docs

    def retrieve(
        self,
        query,
        k=25
    ):

        docs = self.search(
            query=query,
            k=k
        )
        
        print("\n" + "=" * 80)
        print("FAISS QUERY")
        print("=" * 80)
        print(query)
        print("=" * 80)

        return "\n\n".join(
            [
                doc.page_content
                for doc in docs
            ]
        )