from vectorstore.faiss_manager import (
    FAISSManager
)

db = FAISSManager()

results = db.search(
    "quality score"
)

for doc in results:

    print("-" * 50)

    print(doc.page_content)