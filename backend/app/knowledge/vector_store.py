import chromadb
from chromadb.config import Settings as ChromaSettings


class VectorStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "knowledge_base",
    ):
        self.client = chromadb.HttpClient(
            host=host,
            port=port,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_documents(self, documents: list[dict]):
        ids = [
            f"{doc['metadata']['source']}_{doc['metadata']['chunk_index']}"
            for doc in documents
        ]
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = []
        if results["documents"]:
            for i, text in enumerate(results["documents"][0]):
                docs.append(
                    {
                        "text": text,
                        "metadata": (
                            results["metadatas"][0][i] if results["metadatas"] else {}
                        ),
                        "score": (
                            results["distances"][0][i] if results["distances"] else 0
                        ),
                    }
                )
        return docs

    def delete_document(self, doc_id: str):
        self.collection.delete(where={"source": doc_id})

    def list_documents(self) -> list[str]:
        results = self.collection.get()
        sources = set()
        if results["metadatas"]:
            for m in results["metadatas"]:
                if "source" in m:
                    sources.add(m["source"])
        return sorted(sources)
