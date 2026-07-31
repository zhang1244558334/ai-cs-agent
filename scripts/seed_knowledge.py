#!/usr/bin/env python3
"""重新加载 docs/ 目录下所有文档到 Chroma，按 Q&A 对而非固定字数分块"""
import os, sys, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.knowledge.vector_store import VectorStore

DOCS_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs')

def chunk_faq(text: str, source: str) -> list[dict]:
    """按 Q&A 对分块，每对作为一个独立块"""
    chunks = []
    # 按 Q: 分割
    qas = re.split(r'(?=^\*\*Q:)', text, flags=re.MULTILINE)
    for qa in qas:
        qa = qa.strip()
        if len(qa) < 20 or not qa.startswith('**Q:'):
            continue
        chunks.append({
            'text': qa,
            'metadata': {'source': source, 'chunk_index': len(chunks)},
        })
    return chunks

def main():
    vs = VectorStore()
    if not vs.available:
        print("❌ Chroma 不可用")
        return

    # 重建collection以使用中文embedding
    try:
        vs.client.delete_collection("knowledge_base")
        print("已删除旧集合")
    except:
        pass
    vs.collection = vs.client.create_collection(
        name="knowledge_base",
        embedding_function=vs.collection._embedding_function,
    )
    print("已重建集合（BAAI/bge-small-zh-v1.5）")

    md_files = sorted([f for f in os.listdir(DOCS_DIR) if f.endswith('.md')])
    total_chunks = 0

    for fn in md_files:
        fpath = os.path.join(DOCS_DIR, fn)
        with open(fpath, 'r', encoding='utf-8') as f:
            text = f.read()
        chunks = chunk_faq(text, fpath)
        if chunks:
            vs.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"  ✅ {fn} → {len(chunks)} 个Q&A块")

    print(f"\n完成！共加载 {len(md_files)} 个文档，{total_chunks} 个块")

if __name__ == '__main__':
    main()
