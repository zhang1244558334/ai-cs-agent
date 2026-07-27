from fastapi import APIRouter

router = APIRouter()


@router.post("/api/knowledge")
async def upload_doc():
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")


@router.get("/api/knowledge")
async def list_docs():
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")


@router.delete("/api/knowledge/{id}")
async def delete_doc(id: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")
