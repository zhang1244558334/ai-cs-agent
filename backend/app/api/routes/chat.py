from fastapi import APIRouter

router = APIRouter()


@router.post("/api/chats")
async def chat():
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")
