import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings

try:
    from sentence_transformers import SentenceTransformer
    _model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

    class _IntentEmbeddings(chromadb.EmbeddingFunction):
        def __call__(self, input: list[str]) -> list[list[float]]:
            return _model.encode(input, normalize_embeddings=True).tolist()

    EMBED_FN = _IntentEmbeddings()
except Exception:
    EMBED_FN = None

SIMILARITY_THRESHOLD = 0.35


class IntentVectorMatcher:
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8001,
        collection_name: str = "intent_examples",
    ):
        self.collection = None
        try:
            client = chromadb.HttpClient(
                host=host or settings.chroma_host,
                port=port or settings.chroma_port,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            self.collection = client.get_or_create_collection(
                name=collection_name,
                embedding_function=EMBED_FN,
            )
        except Exception:
            self.collection = None

    def query(self, text: str) -> tuple[str, float] | None:
        if not self.collection:
            return None
        try:
            results = self.collection.query(query_texts=[text], n_results=1)
            if not results["documents"] or not results["documents"][0]:
                return None
            distance = results["distances"][0][0] if results["distances"] else 1.0
            similarity = 1.0 - distance
            if similarity < SIMILARITY_THRESHOLD:
                return None
            intent_name = results["documents"][0][0]
            metadata = results["metadatas"][0][0] if results["metadatas"] else {}
            if metadata and "intent" in metadata:
                intent_name = metadata["intent"]
            return intent_name, similarity
        except Exception:
            return None
