import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from app.agents.default_agent import DefaultAgent
from app.agents.price_agent import PriceAgent
from app.agents.langgraph_flows.complaint_flow import complaint_graph, ComplaintState
from app.core.database import async_session
from app.gateway.services.session_mapper import SessionMapper
from app.models.bargain_log import BargainLog
from app.models.message import Message
from app.router.router import Router
from app.safety.keyword_filter import filter_output
from app.safety.prompt_injection import detect_injection

SHADOW_MODE = False

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

    # 输入长度限制
    if len(message) > 500:
        raise HTTPException(status_code=400, detail="message too long (max 500 characters)")

    # 安全检测：注入拦截
    if detect_injection(message):
        intent = "no_reply"
    else:
        intent, graph_sid = await route_engine.route_with_graph(message)

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

        # 转人工不调 LLM
        if intent == "handover":
            full_reply = "正在为您转接人工客服，请稍候..."
            if not SHADOW_MODE:
                yield f"data: {json.dumps({'token': full_reply, 'intent': 'handover'})}\n\n"
            async with async_session() as db:
                msg = Message(session_id=sess.id, role="assistant", content=full_reply, content_type="text", extra_metadata={"intent": "handover"})
                db.add(msg)
                await db.commit()
            yield f"data: {json.dumps({'done': True, 'intent': 'handover', 'session_id': sess.id})}\n\n"
            return

        # 投诉走 LangGraph 流程
        if intent == "complaint":
            initial_state = ComplaintState(
                user_id=user_id or "anonymous",
                message=message,
                session_id=sess.id,
                severity="",
                order_info="",
                policy="",
                solution="",
                user_accepts=False,
                step=0,
            )
            result = await complaint_graph.ainvoke(initial_state)
            full_reply = result.get("solution", "已为您转接人工客服，请稍候。")
            if not SHADOW_MODE:
                yield f"data: {json.dumps({'token': full_reply, 'intent': 'complaint'})}\n\n"

            async with async_session() as db:
                reply_msg = Message(
                    session_id=sess.id,
                    role="assistant",
                    content=full_reply,
                    content_type="text",
                    extra_metadata={"intent": "complaint", "severity": result.get("severity", "")},
                )
                db.add(reply_msg)
                await db.commit()

            yield f"data: {json.dumps({'done': True, 'intent': 'complaint', 'session_id': sess.id})}\n\n"
            return

        # 普通 Agent 回复
        agent = price_agent if intent == "price" else default_agent
        system_msg = {
            "role": "system",
            "content": "你是电商客服助手。回复简洁友好，不超过50字。",
        }
        msgs = [system_msg, {"role": "user", "content": message}]
        async for token in agent.llm.chat_stream(msgs):
            if token == "[DONE]":
                break
            token = filter_output(token)
            full_reply += token
            if not SHADOW_MODE:
                yield f"data: {json.dumps({'token': token, 'intent': intent})}\n\n"

        full_reply = filter_output(full_reply)

        async with async_session() as db:
            reply_msg = Message(
                session_id=sess.id,
                role="assistant",
                content=full_reply,
                content_type="text",
                extra_metadata={"intent": intent, "shadow": SHADOW_MODE},
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

        yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id, 'shadow': SHADOW_MODE})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
