import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.default_agent import DefaultAgent
from app.agents.price_agent import PriceAgent
from app.core.database import async_session
from app.gateway.services.session_mapper import SessionMapper
from app.models.bargain_log import BargainLog
from app.models.message import Message
from app.router.router import Router
from app.safety.keyword_filter import filter_output
from app.safety.prompt_injection import detect_injection

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

    # 安全检测：注入拦截
    if detect_injection(message):
        intent = "no_reply"
    else:
        intent = await route_engine.route(message)

    sess = await session_mapper.get_or_create(
        platform, platform_session_id or "default", user_id or "anonymous"
    )

    async with async_session() as db:
        user_msg = Message(
            session_id=sess.id, role="user", content=message, content_type="text"
        )
        db.add(user_msg)
        await db.commit()

    async def generate():
        full_reply = ""
        # 注入/no_reply 不调 LLM
        if intent == "no_reply":
            full_reply = "抱歉，我无法回答这个问题。如有需要请转人工客服。"
            yield f"data: {json.dumps({'token': full_reply, 'intent': intent})}\n\n"
            yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
            return
        agent = price_agent if intent == "price" else default_agent
        system_msg = {
            "role": "system",
            "content": "你是电商客服助手。回复简洁友好，不超过50字。",
        }
        msgs = [system_msg, {"role": "user", "content": message}]
        async for token in agent.llm.chat_stream(msgs):
            if token == "[DONE]":
                break
            # 输出安全过滤
            token = filter_output(token)
            full_reply += token
            yield f"data: {json.dumps({'token': token, 'intent': intent})}\n\n"
        yield (
            f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
        )

        async with async_session() as db:
            # 完整回复再过滤一次（防止跨 token 漏检）
            full_reply = filter_output(full_reply)
            reply_msg = Message(
                session_id=sess.id,
                role="assistant",
                content=full_reply,
                content_type="text",
                extra_metadata={"intent": intent},
            )
            db.add(reply_msg)
            await db.commit()

            if intent == "price":
                log = BargainLog(
                    session_id=sess.id,
                    round=sess.bargain_count + 1,
                    user_offer=0,
                    agent_offer=0,
                    result="pending",
                )
                db.add(log)
                sess.bargain_count += 1
                await db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")
