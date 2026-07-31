import json
import re
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.agents.default_agent import DefaultAgent
from app.agents.price_agent import PriceAgent
from app.agents.langgraph_flows.complaint_flow import complaint_graph, ComplaintState
from app.core.database import async_session
from app.core.logger import get_logger
from app.gateway.services.session_mapper import SessionMapper
from app.human_handover.handover_manager import HandoverManager
from app.knowledge.retriever import Retriever
from app.models.bargain_log import BargainLog
from app.models.message import Message
from app.router.router import Router
from app.safety.keyword_filter import filter_output
from app.safety.prompt_injection import detect_injection

logger = get_logger("chat")

SHADOW_MODE = False

router = APIRouter()
route_engine = Router()
default_agent = DefaultAgent()
price_agent = PriceAgent()
session_mapper = SessionMapper()
handover_manager = HandoverManager()
retriever = Retriever(alpha=0.7)


def _save_context(context_history, sess, intent, message):
    """handover/no_reply 不存话题，不参与后续指代消解"""
    if intent not in ("handover", "no_reply"):
        context_history.append({"intent": intent, "topic": message[:12]})
        if len(context_history) > 5:
            context_history[:] = context_history[-5:]
        sess.extra_metadata["last_context_time"] = datetime.now(timezone.utc).timestamp()


_ORDER_NO_RE = re.compile(r"(MOCK\d+|\d{8,})")


def _extract_order_no(message: str) -> str | None:
    """从用户消息中提取订单号（MOCK 单号或 8 位以上数字），没有返回 None"""
    m = _ORDER_NO_RE.search(message)
    return m.group(1) if m else None


async def _load_history(session_id: str, exclude_id: str) -> list[dict]:
    """加载最近8条有效对话历史（排除 handover/no_reply 轮次的助手回复）"""
    async with async_session() as db:
        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id, Message.id != exclude_id)
            .order_by(Message.created_at.desc())
            .limit(20)
        )
        msgs = list(result.scalars().all())
    history = []
    for m in reversed(msgs):
        if m.role == "assistant":
            meta = m.extra_metadata or {}
            if meta.get("intent") in ("handover", "no_reply"):
                continue
        history.append({"role": m.role, "content": m.content})
    return history[-8:]


@router.post("/api/chats")
async def chat(
    platform: str = "web",
    platform_session_id: str = "",
    user_id: str = "",
    message: str = "",
):
    request_start = time.time()
    logger.info(
        "chat request",
        extra={"event": "chat_request", "message_preview": message[:50]},
    )
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    if len(message) > 500:
        raise HTTPException(status_code=400, detail="message too long (max 500 characters)")

    # 安全检测
    if detect_injection(message):
        intent = "no_reply"
    else:
        intent, graph_sid = await route_engine.route_with_graph(message)

    sess = await session_mapper.get_or_create(
        platform, platform_session_id or "default", user_id or "anonymous"
    )

    # human 模式下先检查是否超时，超时自动切回 ai
    if sess.mode == "human":
        await handover_manager.check_timeout_human(sess.id)
        sess = await session_mapper.get_or_create(
            platform, platform_session_id or "default", user_id or "anonymous"
        )

    if sess.extra_metadata is None:
        sess.extra_metadata = {}
    context_history = sess.extra_metadata.setdefault("context_history", [])

    # 30分钟无对话，清空上下文
    last_time = sess.extra_metadata.get("last_context_time")
    if last_time:
        elapsed = (datetime.now(timezone.utc).timestamp() - last_time) / 60
        if elapsed > 30:
            context_history.clear()

    # 多轮上下文指代消解：仅用非 handover/no_reply 轮次的话题
    if intent != "no_reply" and len(message) <= 3 and context_history:
        valid_context = [c for c in context_history if c["intent"] not in ("handover", "no_reply")]
        if valid_context:
            last_topic = valid_context[-1]["topic"]
            enriched = f"{last_topic} {message}"
            intent, graph_sid = await route_engine.route_with_graph(enriched)
            message = enriched

    # 保存用户原文（Query重写只用于路由/检索，不覆盖存库的历史）
    original_message = message

    # Query 重写（仅用有效话题）
    if intent != "no_reply" and context_history:
        valid = [h for h in context_history if h["intent"] not in ("handover", "no_reply")]
        if valid:
            ctx = " | ".join(h["topic"] for h in valid[-3:])
            rewritten = await default_agent.llm.chat([
                {"role": "system", "content": (
                    "你是购物用户，正在和客服对话。根据对话历史，把你刚说的这句话"
                    "补全成完整问句（如果已经是完整问句就原样输出）。"
                    "要求：①用第一人称'我' ②保持你的原始意图 ③不要用客服的口吻"
                    "④只输出补全后的问句本身，不要任何解释。"
                )},
                {"role": "user", "content": message},
            ])
            if rewritten and 3 < len(rewritten.strip()) < 500:
                # 重写结果只用于路由和检索，不污染历史
                message = rewritten.strip()

    async with async_session() as db:
        user_msg = Message(
            session_id=sess.id, role="user", content=original_message, content_type="text"
        )
        db.add(user_msg)
        await db.commit()

    async def generate():
        full_reply = ""

        logger.info(
            "chat routed",
            extra={
                "event": "chat_routed",
                "intent": intent,
                "platform_session_id": platform_session_id,
            },
        )

        # no_reply 不调 LLM
        if intent == "no_reply":
            full_reply = "抱歉，我无法回答这个问题。如有需要请转人工客服。"
            yield f"data: {json.dumps({'token': full_reply, 'intent': intent})}\n\n"
            yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
            _save_context(context_history, sess, intent, message)
            async with async_session() as db2:
                db2.add(sess)
                await db2.commit()
            return

        # handover 不调 LLM
        if intent == "handover":
            full_reply = "正在为您转接人工客服，请稍候..."
            if not SHADOW_MODE:
                yield f"data: {json.dumps({'token': full_reply, 'intent': 'handover'})}\n\n"
            async with async_session() as db:
                msg = Message(session_id=sess.id, role="assistant", content=full_reply, content_type="text", extra_metadata={"intent": "handover"})
                db.add(msg)
                _save_context(context_history, sess, intent, message)
                db.add(sess)
                await db.commit()
            yield f"data: {json.dumps({'done': True, 'intent': 'handover', 'session_id': sess.id})}\n\n"
            return

        # complaint 走 LangGraph
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
                _save_context(context_history, sess, intent, message)
                db.add(sess)
                await db.commit()

            yield f"data: {json.dumps({'done': True, 'intent': 'complaint', 'session_id': sess.id})}\n\n"
            return

        # 普通 Agent 回复
        if intent == "after_sale":
            from app.agents.after_sale_agent import AfterSaleAgent
            agent = AfterSaleAgent()
        elif intent == "price":
            agent = price_agent
        elif intent == "tech":
            from app.agents.tech_agent import TechAgent
            agent = TechAgent()
        elif intent == "logistics":
            from app.agents.logistics_agent import LogisticsAgent
            agent = LogisticsAgent()
        else:
            agent = default_agent
        history = await _load_history(sess.id, user_msg.id)
        system_content = (
            "你是电商客服助手。永远以客服身份说话，不要复述用户问题。"
            "用户说'我说了XX'是在纠正你，应当确认并调整。回复简洁友好，不超过50字。"
        )
        if intent in ("after_sale", "price", "default"):
            results = await retriever.retrieve(original_message, top_k=3)
            knowledge = (
                "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"
            )
            system_content = (
                f"{system_content}\n\n参考以下知识回答用户问题，"
                f"如果知识库没有答案请如实告知。\n\n参考知识：\n{knowledge}"
            )
        system_msg = {"role": "system", "content": system_content}
        msgs = [system_msg] + history + [{"role": "user", "content": original_message}]

        # 订单号提取与跨轮存储（当前消息提取到新的优先）
        extracted_order_no = _extract_order_no(original_message)
        if extracted_order_no:
            sess.extra_metadata["order_no"] = extracted_order_no
        order_no = sess.extra_metadata.get("order_no")

        if intent in ("after_sale", "price", "default"):
            stream = agent.llm.chat_stream(msgs)
        elif intent == "tech":
            stream = agent.chat_stream(msgs)
        elif intent == "logistics":
            stream = agent.chat_stream(msgs, order_no=order_no)
        else:
            stream = agent.llm.chat_stream(msgs)
        async for token in stream:
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

            _save_context(context_history, sess, intent, message)
            db.add(sess)
            await db.commit()

        yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id, 'shadow': SHADOW_MODE})}\n\n"
        logger.info(
            "chat done",
            extra={
                "event": "chat_done",
                "intent": intent,
                "session_id": str(sess.id),
                "duration_ms": int((time.time() - request_start) * 1000),
                "reply_len": len(full_reply),
            },
        )

    return StreamingResponse(generate(), media_type="text/event-stream")
