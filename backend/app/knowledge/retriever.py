from .vector_store import VectorStore


class Retriever:
    def __init__(self, vector_store: VectorStore | None = None):
        self.vs = vector_store or VectorStore()

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        return self.vs.search(query, top_k=top_k)
