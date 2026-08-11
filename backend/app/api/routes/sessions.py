from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete

from app.core.database import async_session
from app.models.message import Message
from app.models.session import Session

router = APIRouter()


class BatchDeleteRequest(BaseModel):
    ids: list[str]


@router.get("/api/sessions")
async def list_sessions(limit: int = 20, offset: int = 0, tenant_id: str = "ecommerce"):
    async with async_session() as db:
        result = await db.execute(
            select(Session)
            .where(Session.tenant_id == tenant_id)
            .order_by(Session.updated_at.desc())
            .offset(offset)
            .limit(limit)
        )
        sessions = result.scalars().all()
        return [
            {
                "id": s.id,
                "platform": s.platform,
                "platform_session_id": s.platform_session_id,
                "user_id": s.user_id,
                "item_id": s.item_id,
                "mode": s.mode,
                "last_intent": s.last_intent,
                "bargain_count": s.bargain_count,
                "tenant_id": s.tenant_id,
                "created_at": str(s.created_at) if s.created_at else None,
                "updated_at": str(s.updated_at) if s.updated_at else None,
            }
            for s in sessions
        ]


@router.post("/api/sessions")
async def create_session(
    platform: str = "web",
    platform_session_id: str = "",
    user_id: str = "",
    tenant_id: str = "ecommerce",
):
    async with async_session() as db:
        sess = Session(
            platform=platform,
            platform_session_id=platform_session_id or f"auto_{user_id}",
            user_id=user_id or "anonymous",
            tenant_id=tenant_id,
        )
        db.add(sess)
        await db.commit()
        await db.refresh(sess)
        return {
            "id": sess.id,
            "platform": sess.platform,
            "user_id": sess.user_id,
            "mode": sess.mode,
            "tenant_id": sess.tenant_id,
            "created_at": str(sess.created_at),
        }


@router.get("/api/sessions/{id}")
async def get_session(id: str):
    async with async_session() as db:
        s = await db.get(Session, id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        return {
            "id": s.id,
            "platform": s.platform,
            "platform_session_id": s.platform_session_id,
            "user_id": s.user_id,
            "item_id": s.item_id,
            "mode": s.mode,
            "last_intent": s.last_intent,
            "bargain_count": s.bargain_count,
            "tenant_id": s.tenant_id,
            "created_at": str(s.created_at) if s.created_at else None,
            "updated_at": str(s.updated_at) if s.updated_at else None,
        }


@router.patch("/api/sessions/{id}")
async def update_session(id: str, mode: str | None = None):
    async with async_session() as db:
        s = await db.get(Session, id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        if mode:
            s.mode = mode
        await db.commit()
        return {"id": s.id, "mode": s.mode}


@router.get("/api/sessions/{id}/messages")
async def get_session_messages(id: str, limit: int = 50):
    async with async_session() as db:
        s = await db.get(Session, id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        result = await db.execute(
            select(Message)
            .where(Message.session_id == id)
            .order_by(Message.created_at.asc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "content_type": m.content_type,
                "extra_metadata": m.extra_metadata,
                "created_at": str(m.created_at) if m.created_at else None,
            }
            for m in messages
        ]


@router.delete("/api/sessions/{id}")
async def delete_session(id: str):
    async with async_session() as db:
        s = await db.get(Session, id)
        if not s:
            raise HTTPException(status_code=404, detail="Session not found")
        await db.execute(delete(Message).where(Message.session_id == id))
        await db.delete(s)
        await db.commit()
        return {"ok": True}


@router.post("/api/sessions/batch-delete")
async def batch_delete_sessions(req: BatchDeleteRequest):
    async with async_session() as db:
        for sid in req.ids:
            s = await db.get(Session, sid)
            if s:
                await db.execute(delete(Message).where(Message.session_id == sid))
                await db.delete(s)
        await db.commit()
    return {"ok": True, "deleted": len(req.ids)}
