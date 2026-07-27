from fastapi import APIRouter, HTTPException

from app.agents.default_agent import DefaultAgent
from app.agents.price_agent import PriceAgent
from app.gateway.services.session_mapper import SessionMapper
from app.router.router import Router

router = APIRouter()
route_engine = Router()
default_agent = DefaultAgent()
price_agent = PriceAgent()
session_mapper = SessionMapper()


@router.post("/api/chats")
async def chat(
    platform: str = "web",
    platform_session_id: str = "",
    user_id: str = "",
    message: str = "",
):
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    intent = await route_engine.route(message)

    sess = await session_mapper.get_or_create(
        platform, platform_session_id or "default", user_id or "anonymous"
    )

    if intent == "price":
        reply = await price_agent.generate(
            message, extra_context={"bargain_count": sess.bargain_count}
        )
    else:
        reply = await default_agent.generate(message)

    return {"intent": intent, "reply": reply, "session_id": sess.id}
