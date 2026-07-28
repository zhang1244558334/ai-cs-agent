import os

SUPPORTED_EXTS = {".md", ".txt", ".csv", ".html"}


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 32) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def load_document(file_path: str) -> list[dict]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in SUPPORTED_EXTS:
        raise ValueError(f"Unsupported file type: {ext}")
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()
    chunks = chunk_text(text)
    return [
        {
            "text": chunk,
            "metadata": {"source": file_path, "chunk_index": i},
        }
        for i, chunk in enumerate(chunks)
    ]
