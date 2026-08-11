import os
import re

import jieba
from rank_bm25 import BM25Okapi

DOCS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "docs"))


class KeywordRetriever:
    """基于BM25+结巴分词的检索器，按业务线加载文档，tenant_id隔离"""

    def __init__(self):
        self._cache: dict[str, dict] = {}

    def _load_documents(self, tenant_id: str) -> dict:
        if tenant_id in self._cache:
            return self._cache[tenant_id]

        tenant_dir = os.path.join(DOCS_BASE, tenant_id)
        documents = []
        if not os.path.exists(tenant_dir):
            self._cache[tenant_id] = {"docs": [], "bm25": None, "tokenized_docs": []}
            return self._cache[tenant_id]

        for fname in os.listdir(tenant_dir):
            if fname.endswith((".md", ".txt")):
                path = os.path.join(tenant_dir, fname)
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue
                sections = re.split(r"\n##\s+", text)
                for sec in sections:
                    if len(sec.strip()) > 20:
                        documents.append({"text": sec.strip(), "source": fname})

        # 用jieba分词构建BM25索引
        tokenized_docs = [jieba.lcut(doc["text"]) for doc in documents]
        bm25 = BM25Okapi(tokenized_docs) if documents else None

        self._cache[tenant_id] = {"docs": documents, "bm25": bm25, "tokenized_docs": tokenized_docs}
        return self._cache[tenant_id]

    def _tokenize(self, text: str, docs: list[dict]) -> list[str]:
        """使用jieba分词提取查询关键词"""
        return jieba.lcut(text)

    def search(self, query: str, top_k: int = 3, tenant_id: str = "ecommerce") -> list[dict]:
        cache = self._load_documents(tenant_id)
        docs = cache["docs"]
        bm25 = cache["bm25"]

        if not docs or bm25 is None:
            return []

        keywords = self._tokenize(query, docs)
        scores = bm25.get_scores(keywords)

        scored = [(scores[i], docs[i]) for i in range(len(docs)) if scores[i] > 0]
        scored.sort(key=lambda x: -x[0])

        results = []
        for score, doc in scored[:top_k]:
            snippet = doc["text"][:200]
            if len(doc["text"]) > 200:
                snippet = self._find_relevant_snippet(doc["text"], keywords)
            results.append({
                "text": snippet,
                "metadata": {"source": doc["source"]},
                "score": float(score),
            })
        return results

    def _find_relevant_snippet(self, text: str, keywords: list[str]) -> str:
        paragraphs = text.split("\n")
        best_para = ""
        best_score = 0
        for para in paragraphs:
            if len(para.strip()) < 10:
                continue
            score = sum(1 for kw in keywords if kw.lower() in para.lower())
            if score > best_score:
                best_score = score
                best_para = para.strip()
        return best_para[:200] if best_para else text[:200]

    async def retrieve(self, query: str, top_k: int = 3, tenant_id: str = "ecommerce") -> list[dict]:
        return self.search(query, top_k=top_k, tenant_id=tenant_id)
