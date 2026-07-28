import os
import re


class KeywordRetriever:
    """基于关键词匹配的轻量级检索器，无需嵌入模型"""

    def __init__(self, docs_dir: str = "docs"):
        self.docs_dir = docs_dir
        self.documents = []  # list of {"text": str, "source": str}
        self._load_documents()

    def _load_documents(self):
        if not os.path.exists(self.docs_dir):
            return
        for fname in os.listdir(self.docs_dir):
            if fname.endswith((".md", ".txt")):
                path = os.path.join(self.docs_dir, fname)
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
                # 按标题切块
                sections = re.split(r"\n##\s+", text)
                for sec in sections:
                    if len(sec.strip()) > 20:
                        self.documents.append({"text": sec.strip(), "source": fname})

    def search(self, query: str, top_k: int = 3) -> list[dict]:
        """关键词检索：将查询分词后在文档中匹配"""
        if not self.documents:
            return []

        keywords = self._tokenize(query)
        scored = []
        for doc in self.documents:
            text_lower = doc["text"].lower()
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: -x[0])
        results = []
        for score, doc in scored[:top_k]:
            snippet = doc["text"][:200]
            if len(doc["text"]) > 200:
                snippet = self._find_relevant_snippet(doc["text"], keywords)
            results.append({
                "text": snippet,
                "metadata": {"source": doc["source"]},
                "score": score / max(len(keywords), 1),
            })
        return results

    def _tokenize(self, text: str) -> list[str]:
        """简单中文分词：按字/词切分"""
        text = text.lower()
        # 提取关键词（2-4字的中文片段）
        tokens = []
        # 常用商品/服务关键词
        for word in [
            "退货", "退款", "换货", "保修", "维修", "发货", "物流",
            "快递", "包邮", "运费", "价格", "优惠", "折扣", "促销",
            "尺码", "颜色", "型号", "规格", "参数",
            "客服", "人工", "投诉", "售后",
        ]:
            if word in text:
                tokens.append(word)
        if not tokens:
            # 按字切分作为后备
            for i in range(len(text) - 1):
                tokens.append(text[i : i + 2])
        return list(set(tokens))

    def _find_relevant_snippet(self, text: str, keywords: list[str]) -> str:
        """找到包含最多关键词的段落"""
        paragraphs = text.split("\n")
        best_para = ""
        best_score = 0
        for para in paragraphs:
            if len(para.strip()) < 10:
                continue
            score = sum(1 for kw in keywords if kw in para.lower())
            if score > best_score:
                best_score = score
                best_para = para.strip()
        return best_para[:200] if best_para else text[:200]

    async def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        return self.search(query, top_k=top_k)
