# vectorstore/build_index.py

import json
from pathlib import Path

from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS

from vectorstore.embeddings import (
    get_embeddings
)


class IndexBuilder:

    def __init__(self):

        self.embeddings = (
            get_embeddings()
        )

    def _normalize_content(
        self,
        content
    ) -> str:

        if content is None:

            return ""

        if isinstance(
            content,
            str
        ):

            return content.strip()

        if isinstance(
            content,
            dict
        ):

            return "\n".join(
                [
                    f"{key}: {value}"
                    for key, value in content.items()
                ]
            )

        if isinstance(
            content,
            list
        ):

            return "\n".join(
                [
                    str(item)
                    for item in content
                ]
            )

        return str(content)

    def _create_document(
        self,
        item: dict
    ):

        document_type = item.get(
            "document_type",
            "unknown"
        )

        name = (
            item.get("column_name")
            or item.get("name")
            or "Unknown"
        )

        data_type = (
            item.get("data_type")
            or item.get("datatype")
            or "Unknown"
        )

        definition = (
            item.get("definition")
            or item.get("business_meaning")
            or "Not Available"
        )

        semantic_type = (
            item.get("semantic_type")
            or document_type
        )

        # ======================================
        # NORMALIZE CONTENT
        # ======================================

        content = self._normalize_content(
            item.get("content")
        )

        if not content:

            content = f"""
Document Type: {document_type}

Name: {name}

Data Type: {data_type}

Semantic Type: {semantic_type}

Definition: {definition}
""".strip()

        return Document(
            page_content=content,
            metadata={

                "name":
                    item.get("name"),

                "document_type":
                    document_type,

                "schema_name":
                    item.get(
                        "schema_name"
                    ),

                "table_name":
                    item.get(
                        "table_name"
                    ),

                "column_name":
                    item.get(
                        "column_name"
                    ),

                "data_type":
                    item.get(
                        "data_type"
                    ),

                "semantic_type":
                    semantic_type
            }
        )

    def build(
        self,
        metadata_file,
        index_path="vectorstore/index"
    ):

        with open(
            metadata_file,
            "r",
            encoding="utf-8"
        ) as f:

            metadata = json.load(f)

        documents = []

        for idx, item in enumerate(
            metadata,
            start=1
        ):

            try:

                doc = (
                    self._create_document(
                        item
                    )
                )

                documents.append(
                    doc
                )

            except Exception as ex:

                print(
                    f"Skipping document "
                    f"{idx}: {str(ex)}"
                )

        if not documents:

            raise ValueError(
                "No documents created "
                "for indexing."
            )

        print(
            f"\nCreating FAISS index with "
            f"{len(documents)} documents..."
            )
            
        vector_store = (
            
            FAISS.from_documents(
            documents,
            self.embeddings
            )
            )
        
        Path(
            
            index_path
            ).parent.mkdir(
            parents=True,
            exist_ok=True
            )
    
        vector_store.save_local(
            index_path
            )
        
        print(
            f"\nFAISS Index saved to "
            f"{index_path}"
            )
        
        return len(documents)


if __name__ == "__main__":

    builder = IndexBuilder()

    count = builder.build(
        "metadata/metadata_repository.json"
    )

    print(
        f"\nIndexed "
        f"{count} documents"
    )