"""
ProductIndexer: 将闲鱼商品信息转为QA对存入ChromaDB知识库。
单例模式，用于自动/手动灌入商品知识。
"""
import re

from .retriever import Retriever


# ── 材质提取 ──
_MATERIAL_PATTERNS = [
    r"(?:材质|面料|材料|质地)[：:是为]*[\s]*(.+?)(?:[，。,\.\n]|$)",
    r"(纯棉|真丝|丝绸|羊毛|羊绒|亚麻|棉麻|雪纺|牛仔|皮革|PU皮|帆布|蕾丝|针织|毛呢|羽绒|莫代尔|天丝)",
    r"(\d+%[棉丝毛麻涤纶])",
]


def _extract_material(desc: str) -> str:
    """从描述中提取材质相关信息"""
    for pat in _MATERIAL_PATTERNS:
        m = re.search(pat, desc)
        if m:
            return m.group(1).strip()[:50]
    return ""


# ── QA 构建 ──
def _build_qa_pairs(item_id: str, item: dict) -> list[dict]:
    """把商品信息转成 QA 对列表，每项为 {text, metadata}"""
    title = item.get("title", "")
    price = item.get("soldPrice", "")
    desc = item.get("desc", "")
    labels = item.get("itemLabelExtList", [])
    category = labels[0].get("valueText", "") if labels else ""

    base_meta = {
        "source": f"xianyu_item_{item_id}",
        "tenant_id": "ecommerce",
        "chunk_type": "product_qa",
    }

    pairs = []
    idx = 0

    if title:
        meta = {**base_meta, "chunk_index": idx}
        pairs.append({"text": f"问：商品标题是什么？\n答：{title}", "metadata": meta})
        idx += 1

    material = _extract_material(desc) if desc else ""
    if material:
        meta = {**base_meta, "chunk_index": idx}
        pairs.append({"text": f"问：什么材质？\n答：{material}", "metadata": meta})
        idx += 1

    if price:
        meta = {**base_meta, "chunk_index": idx}
        pairs.append({"text": f"问：多少钱？什么价格？\n答：¥{price}", "metadata": meta})
        idx += 1

    if desc:
        meta = {**base_meta, "chunk_index": idx}
        snippet = desc[:200].replace("\n", " ")
        pairs.append({"text": f"问：商品描述？\n答：{snippet}", "metadata": meta})
        idx += 1

    if category:
        meta = {**base_meta, "chunk_index": idx}
        pairs.append({"text": f"问：什么分类？\n答：{category}", "metadata": meta})
        idx += 1

    return pairs


class ProductIndexer:
    """单例：商品知识索引器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.retriever = Retriever()

    def _exists(self, item_id: str) -> bool:
        """检查是否已有同 source 的问答"""
        vs = self.retriever.vs
        if not vs.available:
            return False
        source = f"xianyu_item_{item_id}"
        try:
            result = vs.collection.get(where={"source": source})
            ids = result.get("ids", [])
            return len(ids) > 0
        except Exception:
            return False

    def index_item(self, item_id: str, item_info_dict: dict) -> bool:
        """将单个商品转成QA对存入ChromaDB。返回 True 表示成功"""
        try:
            if self._exists(item_id):
                print(f"[ProductIndexer] 商品 {item_id} 已存在，跳过")
                return False

            pairs = _build_qa_pairs(item_id, item_info_dict)
            if not pairs:
                return False

            self.retriever.vs.add_documents(pairs)
            print(f"[ProductIndexer] 商品 {item_id} 已索引 ({len(pairs)} 条QA)")
            return True
        except Exception as e:
            print(f"[ProductIndexer] 索引商品 {item_id} 失败: {e}")
            return False
