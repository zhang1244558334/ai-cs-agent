import os
import tempfile

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.knowledge.keyword_retriever import KeywordRetriever
from app.knowledge.loader import load_document
from app.knowledge.vector_store import VectorStore

router = APIRouter()
_vs: VectorStore | None = None


def get_vs() -> VectorStore:
    global _vs
    if _vs is None:
        _vs = VectorStore()
    return _vs


@router.post("/api/knowledge")
async def upload_doc(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".txt", ".csv", ".html"]:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        docs = load_document(tmp_path)
        get_vs().add_documents(docs)
        return {
            "message": f"Uploaded {len(docs)} chunks from {file.filename}",
            "chunks": len(docs),
        }
    finally:
        os.unlink(tmp_path)


@router.get("/api/knowledge")
async def list_docs():
    return {"documents": get_vs().list_documents()}


@router.delete("/api/knowledge/{source}")
async def delete_doc(source: str):
    get_vs().delete_document(source)
    return {"message": f"Deleted: {source}"}


@router.patch("/api/knowledge/{source}")
async def update_doc(source: str, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".txt", ".csv", ".html"]:
        raise HTTPException(400, f"Unsupported: {ext}")
    get_vs().delete_document(source)
    content = await file.read()
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    try:
        docs = load_document(tmp_path)
        get_vs().add_documents(docs)
        return {"message": f"Updated {len(docs)} chunks", "chunks": len(docs)}
    finally:
        os.unlink(tmp_path)


@router.post("/api/knowledge/search")
async def search_knowledge(query: str, top_k: int = 3):
    kr = KeywordRetriever()
    results = await kr.retrieve(query, top_k=top_k)
    return {"results": results}
