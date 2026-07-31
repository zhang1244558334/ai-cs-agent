from .keyword_retriever import KeywordRetriever
from .vector_store import VectorStore


class Retriever:
    def __init__(self, vector_store: VectorStore | None = None, alpha: float = 0.6):
        self.vs = vector_store or VectorStore()
        self.kr = KeywordRetriever()
        self.alpha = alpha

    async def retrieve(self, query: str, top_k: int = 3, tenant_id: str = "single") -> list[dict]:
        # 多租户模式：只搜本租户私有知识 + 公共知识
        if tenant_id and tenant_id != "single":
            where_private = {"tenant_id": tenant_id}
            where_public = {"is_public": True}
            vector_private = self.vs.search(query, top_k=top_k * 2, where=where_private)
            vector_public = self.vs.search(query, top_k=top_k * 2, where=where_public)
            vector_results = vector_private + vector_public
        else:
            vector_results = self.vs.search(query, top_k=top_k * 2)
        keyword_results = self.kr.search(query, top_k=top_k * 2)

        merged: dict[str, dict] = {}
        for r in vector_results:
            merged[r["text"]] = {
                "text": r["text"],
                "metadata": r.get("metadata", {}),
                "vector_sim": 1.0 - r["score"],
                "keyword_score": 0.0,
            }
        for r in keyword_results:
            if r["text"] in merged:
                merged[r["text"]]["keyword_score"] = r["score"]
            else:
                merged[r["text"]] = {
                    "text": r["text"],
                    "metadata": r.get("metadata", {}),
                    "vector_sim": 0.0,
                    "keyword_score": r["score"],
                }

        for v in merged.values():
            v["score"] = self.alpha * v["vector_sim"] + (1.0 - self.alpha) * v["keyword_score"]

        results = sorted(merged.values(), key=lambda x: -x["score"])[:top_k]
        for r in results:
            r.pop("vector_sim", None)
            r.pop("keyword_score", None)
        return results
