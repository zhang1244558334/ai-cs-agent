#!/usr/bin/env python3
"""重新加载 docs/ 目录下所有文档到 Chroma，按租户隔离"""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.knowledge.vector_store import VectorStore

DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')

TENANT_MAP = {
    'ecommerce': 'ecommerce',
    'xianyu': 'xianyu',
    'property': 'property',
}


def chunk_faq(text: str, source: str) -> list[dict]:
    """按 Q&A 对分块，支持 **Q: 和 ## 标题两种格式"""
    chunks = []
    # 兼容两种格式：**Q: ... 和 ## 标题
    # 先统一标注：把所有 ## 标题包装成 Q: 格式
    text = re.sub(r'(?m)^## (.+)', r'\n**Q:\1**\n', text)
    # 按 Q: 分割
    qas = re.split(r'(?=^\*\*Q:)', text, flags=re.MULTILINE)
    for qa in qas:
        qa = qa.strip()
        if len(qa) < 20 or not qa.startswith('**Q:'):
            continue
        chunks.append({
            'text': qa,
            'metadata': {
                'source': source,
                'chunk_index': len(chunks),
            },
        })
    return chunks


def chunk_markdown(text: str, source: str, max_chars: int = 500) -> list[dict]:
    """兜底分块：按固定字数切"""
    chunks = []
    text = text.strip()
    if not text:
        return chunks
    for i in range(0, len(text), max_chars):
        chunk = text[i:i + max_chars].strip()
        if len(chunk) < 20:
            continue
        chunks.append({
            'text': chunk,
            'metadata': {
                'source': source,
                'chunk_index': len(chunks),
            },
        })
    return chunks


def main():
    vs = VectorStore()
    if not vs.available:
        print("❌ Chroma 不可用")
        return

    # 重建 collection
    try:
        vs.client.delete_collection("knowledge_base")
        print("已删除旧集合")
    except Exception:
        pass
    vs.collection = vs.client.create_collection(
        name="knowledge_base",
        embedding_function=vs.collection._embedding_function,
    )
    print("已重建集合（BAAI/bge-small-zh-v1.5）\n")

    total_chunks = 0
    tenant_counts = {}

    # 递归扫描 docs/ 子目录
    for tenant_dir, tenant_id in TENANT_MAP.items():
        tenant_path = os.path.join(DOCS_DIR, tenant_dir)
        if not os.path.isdir(tenant_path):
            continue

        md_files = sorted([
            f for f in os.listdir(tenant_path) if f.endswith('.md')
        ])
        if not md_files:
            continue

        print(f"📂 {tenant_dir} ({tenant_id}):")
        tenant_chunks = 0

        for fn in md_files:
            fpath = os.path.join(tenant_path, fn)
            with open(fpath, 'r', encoding='utf-8') as f:
                text = f.read()

            # 先尝试 Q&A 分块
            chunks = chunk_faq(text, fn)
            if not chunks:
                chunks = chunk_markdown(text, fn)

            if chunks:
                # 注入 tenant_id
                for c in chunks:
                    c['metadata']['tenant_id'] = tenant_id

                # 逐批写入
                ids = [
                    f"{tenant_id}/{c['metadata']['source']}_{c['metadata']['chunk_index']}"
                    for c in chunks
                ]
                texts = [c['text'] for c in chunks]
                metadatas = [c['metadata'] for c in chunks]
                vs.collection.add(documents=texts, metadatas=metadatas, ids=ids)

                tenant_chunks += len(chunks)
                print(f"  ✅ {fn} → {len(chunks)} 块")

        tenant_counts[tenant_id] = tenant_chunks
        total_chunks += tenant_chunks
        print(f"     小计: {tenant_chunks} 块\n")

    print(f"完成！共 {len(tenant_counts)} 个租户，{total_chunks} 个块:")
    for tid, count in tenant_counts.items():
        print(f"  • {tid}: {count} 块")

    # 验证检索
    print("\n🔍 验证检索...")
    results_ecom = vs.search("退换货政策", top_k=2, where={"tenant_id": "ecommerce"})
    results_xy = vs.search("退换货政策", top_k=2, where={"tenant_id": "xianyu"})
    print(f"  ecommerce 搜到: {len(results_ecom)} 条")
    print(f"  xianyu 搜到: {len(results_xy)} 条")
    if results_ecom and results_xy:
        print("  ✅ 租户隔离生效")


if __name__ == '__main__':
    main()
