from fastapi import APIRouter

router = APIRouter()


@router.get("/api/sessions")
async def list_sessions():
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")


@router.post("/api/sessions")
async def create_session():
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")


@router.get("/api/sessions/{id}")
async def get_session(id: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")


@router.patch("/api/sessions/{id}")
async def update_session(id: str):
    from fastapi import HTTPException

    raise HTTPException(status_code=501, detail="Not Implemented")
