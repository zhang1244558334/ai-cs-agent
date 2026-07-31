import chromadb
from chromadb.config import Settings as ChromaSettings

try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

    class _ChineseEmbeddings(chromadb.EmbeddingFunction):
        def __call__(self, input: list[str]) -> list[list[float]]:
            return _model.encode(input, normalize_embeddings=True).tolist()

    EMBED_FN = _ChineseEmbeddings()
    print("[VectorStore] Using BAAI/bge-small-zh-v1.5")
except Exception as e:
    EMBED_FN = None
    print(f"[VectorStore] Failed to load Chinese embedding model: {e}")


class VectorStore:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "knowledge_base",
    ):
        try:
            self.client = chromadb.HttpClient(
                host=host,
                port=port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = self.client.get_or_create_collection(
                name=collection_name,
                embedding_function=EMBED_FN,
            )
            self.available = True
        except Exception as e:
            print(f"[VectorStore] Chroma not available: {e}")
            self.available = False
            self._memory: list[dict] = []

    def add_documents(self, documents: list[dict]):
        if not self.available:
            self._memory.extend(documents)
            return
        ids = [
            f"{doc['metadata']['source']}_{doc['metadata']['chunk_index']}"
            for doc in documents
        ]
        texts = [doc["text"] for doc in documents]
        metadatas = [doc["metadata"] for doc in documents]
        self.collection.add(documents=texts, metadatas=metadatas, ids=ids)

    def search(self, query: str, top_k: int = 3, where: dict | None = None) -> list[dict]:
        if not self.available:
            return []
        results = self.collection.query(
            query_texts=[query], n_results=top_k, where=where
        )
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
        if not self.available:
            return
        self.collection.delete(where={"source": doc_id})

    def list_documents(self) -> list[str]:
        if not self.available:
            return []
        results = self.collection.get()
        sources = set()
        if results["metadatas"]:
            for m in results["metadatas"]:
                if "source" in m:
                    sources.add(m["source"])
        return sorted(sources)
