import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.knowledge.deidentify import deidentify
from app.knowledge.retriever import Retriever
from app.knowledge.loader import load_document
from app.knowledge.vector_store import VectorStore

router = APIRouter()
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))


@router.post("/api/knowledge")
async def upload_doc(file: UploadFile = File(...), tenant_id: str = "single", is_public: bool = False):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".txt", ".csv", ".html"]:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    content = await file.read()
    text_content = content.decode("utf-8", errors="ignore")

    # 公共知识去标识化
    if is_public:
        text_content = deidentify(text_content)

    dest = os.path.join(DOCS_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(text_content.encode("utf-8"))
    docs = load_document(dest, tenant_id=tenant_id, is_public=is_public)
    vs = VectorStore()
    vs.add_documents(docs)
    return {
        "message": f"Uploaded {file.filename}",
        "chunks": len(docs),
        "is_public": is_public,
    }


@router.get("/api/knowledge")
async def list_docs():
    if not os.path.exists(DOCS_DIR):
        return {"documents": []}
    files = [
        f for f in os.listdir(DOCS_DIR)
        if f.endswith((".md", ".txt", ".csv", ".html"))
    ]
    return {"documents": files}


@router.delete("/api/knowledge/{source}")
async def delete_doc(source: str):
    filepath = os.path.join(DOCS_DIR, source)
    if not os.path.exists(filepath):
        raise HTTPException(404, f"File not found: {source}")
    os.remove(filepath)

    # 同步删除 Chroma 中的向量（source 可能是不同格式的路径，逐一尝试）
    candidates = {
        filepath,
        os.path.join(PROJECT_ROOT, "scripts", "..", "docs", source),
    }
    vs = VectorStore()
    for candidate in candidates:
        vs.delete_document(candidate)
    return {"message": f"Deleted: {source}"}


@router.patch("/api/knowledge/{source}")
async def update_doc(
    source: str,
    file: UploadFile = File(...),
    tenant_id: str = "single",
    is_public: bool = False,
):
    filepath = os.path.join(DOCS_DIR, source)
    if not os.path.exists(filepath):
        raise HTTPException(404, f"File not found: {source}")
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # 向量库同步：先清旧向量，再写入新内容
    vs = VectorStore()
    vs.delete_document(filepath)
    docs = load_document(filepath, tenant_id=tenant_id, is_public=is_public)
    vs.add_documents(docs)
    return {"message": f"Updated {source}", "chunks": len(docs)}


@router.post("/api/knowledge/search")
async def search_knowledge(query: str, top_k: int = 3, alpha: float = 0.6, tenant_id: str = "single"):
    hybrid = Retriever(alpha=alpha)
    results = await hybrid.retrieve(query, top_k=top_k, tenant_id=tenant_id)
    return {"results": results}
