import os
import shutil

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.knowledge.keyword_retriever import KeywordRetriever
from app.knowledge.loader import load_document

router = APIRouter()
DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))


@router.post("/api/knowledge")
async def upload_doc(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".md", ".txt", ".csv", ".html"]:
        raise HTTPException(400, f"Unsupported file type: {ext}")
    content = await file.read()
    dest = os.path.join(DOCS_DIR, file.filename)
    with open(dest, "wb") as f:
        f.write(content)
    return {"message": f"Uploaded {file.filename}", "chunks": len(load_document(dest))}


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
    if os.path.exists(filepath):
        os.remove(filepath)
        return {"message": f"Deleted: {source}"}
    raise HTTPException(404, f"File not found: {source}")


@router.patch("/api/knowledge/{source}")
async def update_doc(source: str, file: UploadFile = File(...)):
    filepath = os.path.join(DOCS_DIR, source)
    if not os.path.exists(filepath):
        raise HTTPException(404, f"File not found: {source}")
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    return {"message": f"Updated {source}"}


@router.post("/api/knowledge/search")
async def search_knowledge(query: str, top_k: int = 3):
    kr = KeywordRetriever()
    results = await kr.retrieve(query, top_k=top_k)
    return {"results": results}
