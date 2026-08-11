import json
import os
import re
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update

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
from app.models.session import Session
from app.router.router import Router
from app.safety.keyword_filter import filter_output
from app.forms.engine import FormEngine
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
form_engine = FormEngine()


def _save_context(context_history, sess, intent, message):
    """handover/no_reply 不存话题，不参与后续指代消解"""
    if intent not in ("handover", "no_reply"):
        context_history.append({"intent": intent, "topic": message[:12]})
        if len(context_history) > 8:
            context_history[:] = context_history[-8:]
        sess.extra_metadata["last_context_time"] = datetime.now(timezone.utc).timestamp()


_ORDER_NO_RE = re.compile(r"(MOCK\d+|\d{8,})")


def _extract_order_no(message: str) -> str | None:
    """从用户消息中提取订单号（MOCK 单号或 8 位以上数字），没有返回 None"""
    m = _ORDER_NO_RE.search(message)
    return m.group(1) if m else None


def _quality_check(full_reply: str, retrieval_results: list) -> dict:
    if "未找到相关信息" in full_reply:
        return {}
    if not retrieval_results:
        return {}
    reply_bigrams = set()
    for i in range(len(full_reply) - 1):
        bi = full_reply[i : i + 2]
        if "\u4e00" <= bi[0] <= "\u9fff" and "\u4e00" <= bi[1] <= "\u9fff":
            reply_bigrams.add(bi)
    if not reply_bigrams:
        return {}
    best_overlap = 0
    for r in retrieval_results:
        text = r.get("text", "")
        kb_bigrams = set()
        for i in range(len(text) - 1):
            bi = text[i : i + 2]
            if "\u4e00" <= bi[0] <= "\u9fff" and "\u4e00" <= bi[1] <= "\u9fff":
                kb_bigrams.add(bi)
        overlap = len(reply_bigrams & kb_bigrams)
        if overlap > best_overlap:
            best_overlap = overlap
    if best_overlap < 3:
        return {"quality_flag": "factual_error", "quality_score": 0.0}
    return {}


async def generate_reply(message: str, user_id: str, tenant_id: str = "ecommerce", item_info: str = "") -> dict:
    """生成非流式回复，供主流程和外部Bot（如XianyuBot）复用。

    返回 {"reply": str, "intent": str}
    """
    # 1. 意图路由
    intent, _ = await route_engine.route_with_graph(message, tenant_id=tenant_id)

    # 2. handover / no_reply 兜底
    if intent == "no_reply":
        return {"reply": "抱歉，我无法回答这个问题。如有需要请转人工客服。", "intent": intent}
    if intent == "handover":
        return {"reply": "正在为您转接人工客服，请稍候...", "intent": intent}

    # 3. complaint 走 LangGraph
    if intent == "complaint":
        initial_state = ComplaintState(
            user_id=user_id or "anonymous",
            message=message,
            session_id="",
            severity="",
            order_info="",
            policy="",
            solution="",
            user_accepts=False,
            step=0,
        )
        result = await complaint_graph.ainvoke(initial_state)
        reply = result.get("solution", "已为您转接人工客服，请稍候。")
        return {"reply": reply, "intent": intent}

    # 4. Agent 调度（与 /chat 接口一致）
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

    # 5. 加载业务 prompt
    system_content = _load_business_prompt(tenant_id)

    # 6. RAG（仅 price / default 等意图才检索，问候语跳过）
    _rag_intents = {"price", "default", "fee", "repair", "complain", "notice"}
    if intent in _rag_intents:
        greeting_patterns = ["您好", "你好", "在吗", "嗨", "哈喽", "早上好", "下午好", "晚上好"]
        is_greeting = len(message.strip()) <= 5 or any(g in message for g in greeting_patterns)
        if is_greeting:
            results = []
        else:
            results = await retriever.retrieve(message, top_k=3, tenant_id=tenant_id)
        knowledge = (
            "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"
        )
        system_content = (
            f"{system_content}\n\n参考以下知识回答用户问题，"
            f"如果知识库没有答案请如实告知。\n\n参考知识：\n{knowledge}"
        )

    # 7. 注入商品信息
    if item_info:
        system_content = f"{system_content}\n\n当前咨询的商品：\n{item_info}"

    # 8. 构建消息并生成（非流式）
    msgs = [{"role": "system", "content": system_content}, {"role": "user", "content": message}]
    reply = await agent.llm.chat(msgs)
    reply = reply.strip()

    return {"reply": reply, "intent": intent}


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


def _load_business_prompt(tenant_id: str) -> str:
    """加载业务线自定义prompt，如无则返回默认电商prompt"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "businesses.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            businesses = json.load(f)
        for b in businesses:
            if b["id"] == tenant_id and b.get("prompt"):
                return b["prompt"]
    except Exception:
        pass
    return "你是电商平台客服助手。"


@router.post("/api/chats")
async def chat(
    platform: str = "web",
    platform_session_id: str = "",
    user_id: str = "",
    message: str = "",
    tenant_id: str = "ecommerce",
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
        intent, graph_sid = await route_engine.route_with_graph(message, tenant_id=tenant_id)

    sess = await session_mapper.get_or_create(
        platform, platform_session_id or "default", user_id or "anonymous", tenant_id=tenant_id
    )

    # human 模式下先检查是否超时，超时自动切回 ai
    if sess.mode == "human":
        await handover_manager.check_timeout_human(sess.id)
        sess = await session_mapper.get_or_create(
            platform, platform_session_id or "default", user_id or "anonymous", tenant_id=tenant_id
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

    # 表单进行中：超时检查 & 保存原始路由intent用于后续比对
    form_state = sess.extra_metadata.get("form_state") if sess.extra_metadata else None
    form_active = form_state and form_state.get("status") in ("collecting", "confirming")
    if form_active:
        # 超时自动清除（5分钟）
        started_at = form_state.get("started_at")
        if started_at and (time.time() - started_at) > 300:
            form_state = None
            form_active = False
            sess.extra_metadata["form_state"] = None
    _routed_intent = intent  # 保存原始路由intent，供表单阶段比对
    # 多轮上下文指代消解（表单进行中时跳过，避免覆盖intent）
    if not form_active and intent not in ("no_reply", "handover") and len(message) <= 3 and context_history:
        valid_context = [c for c in context_history if c["intent"] not in ("handover", "no_reply")]
        if valid_context:
            last_topic = valid_context[-1]["topic"]
            # topic 是 message[:12] 截断，若含 MOCK 说明订单号被截断，用完整单号还原
            if sess.extra_metadata.get("order_no") and "MOCK" in last_topic:
                last_topic = f"订单号 {sess.extra_metadata['order_no']}"
            enriched = f"{last_topic} {message}"
            intent, graph_sid = await route_engine.route_with_graph(enriched, tenant_id=tenant_id)
            message = enriched

    # 订单号上下文路由补丁：仅当"当前消息含订单号"或"短指代且会话已存订单号"且最近话题是物流
    # 才强制 logistics；handover/complaint/no_reply 是明确意图不被覆盖。
    # （否则"订单号 MOCKxxx"会被 LLM 分到 default/tech，轨迹查询逻辑走不到）
    if intent not in ("logistics", "handover", "complaint", "no_reply"):
        recent_intents = [c["intent"] for c in context_history[-3:]]
        msg_order = _extract_order_no(message)
        if "logistics" in recent_intents and (
            msg_order or (len(message) <= 3 and sess.extra_metadata.get("order_no"))
        ):
            intent = "logistics"

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
            session_id=sess.id, role="user", content=original_message, content_type="text",
            tenant_id=tenant_id,
        )
        db.add(user_msg)
        await db.commit()

    async def generate():
        nonlocal form_active, form_state
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
                msg = Message(session_id=sess.id, role="assistant", content=full_reply, content_type="text", extra_metadata={"intent": "handover"}, tenant_id=tenant_id)
                db.add(msg)
                _save_context(context_history, sess, intent, message)
                db.add(sess)
                await db.commit()
            yield f"data: {json.dumps({'done': True, 'intent': 'handover', 'session_id': sess.id})}\n\n"
            return

        # === 多轮表单引擎 ===
        # 活跃表单检查：取消词优先在任何时候生效，意图不匹配则清除走正常流程
        _skip_form_block = False
        if form_active:
            _is_cancel = any(w in original_message for w in ["取消", "算了", "不用了"])
            if _is_cancel:
                sess.extra_metadata["form_state"] = None
                async with async_session() as db2:
                    await db2.execute(
                        update(Session).where(Session.id == sess.id).values(extra_metadata=sess.extra_metadata)
                    )
                    await db2.commit()
                yield f"data: {json.dumps({'token': '已取消当前操作，有什么可以帮您的？', 'intent': intent})}\n\n"
                yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
                return
            _form_intent = form_state.get("intent") if form_state else None
            if _form_intent and _routed_intent != _form_intent:
                # 意图不匹配：自动清除表单状态，走正常 Agent 回复
                sess.extra_metadata["form_state"] = None
                form_state = None
                form_active = False
                _skip_form_block = True
                async with async_session() as db2:
                    await db2.execute(
                        update(Session).where(Session.id == sess.id).values(extra_metadata=sess.extra_metadata)
                    )
                    await db2.commit()
                # 不 return，继续走正常流程

        form_intents = form_engine.get_form_intents(tenant_id)
        # 售后Agent直通：消息中已含操作词或订单号时，跳过表单直接交给Agent处理
        _action_keywords = ["帮我退", "申请退货", "我要退", "退款", "退货"]
        _has_action = any(kw in original_message for kw in _action_keywords)
        _has_order = bool(_extract_order_no(original_message))
        _skip_form = intent == "after_sale" and (_has_action or _has_order)
        if not _skip_form_block and intent in form_intents and not _skip_form:
            form_state = sess.extra_metadata.get("form_state")

            if form_state is None or form_state.get("status") == "done":
                form_state, first_prompt = form_engine.start(intent, tenant_id, trigger_message=original_message)
                sess.extra_metadata["form_state"] = form_state
                async with async_session() as db2:
                    await db2.execute(
                        update(Session).where(Session.id == sess.id).values(extra_metadata=sess.extra_metadata)
                    )
                    await db2.commit()
                template = form_engine.get_template(intent, tenant_id)
                idx = form_state.get("current_slot_index", 0)
                first_field = template.slots[idx].name if template and idx < len(template.slots) else ""
                first_label = template.slots[idx].label if template and idx < len(template.slots) else ""
                yield f"data: {json.dumps({'type': 'form_slot', 'intent': intent, 'field': first_field, 'label': first_label, 'prompt': first_prompt})}\n\n"
                yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
                return

            if any(w in original_message for w in ["取消", "算了", "不用了"]):
                sess.extra_metadata["form_state"] = None
                async with async_session() as db2:
                    await db2.execute(
                        update(Session).where(Session.id == sess.id).values(extra_metadata=sess.extra_metadata)
                    )
                    await db2.commit()
                yield f"data: {json.dumps({'token': '已取消当前操作，有什么可以帮您的？', 'intent': intent})}\n\n"
                yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
                return

            result = form_engine.process(original_message, form_state, intent, tenant_id)
            sess.extra_metadata["form_state"] = form_state
            async with async_session() as db2:
                await db2.execute(
                    update(Session).where(Session.id == sess.id).values(extra_metadata=sess.extra_metadata)
                )
                await db2.commit()

            if result["type"] == "form_done":
                full_reply = result["result"]
                yield f"data: {json.dumps({'type': 'form_done', 'intent': intent, 'result': full_reply})}\n\n"
                yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
                async with async_session() as db2:
                    reply_msg = Message(session_id=sess.id, role="assistant", content=full_reply, content_type="text", extra_metadata={"intent": intent, "form_result": True}, tenant_id=tenant_id)
                    db2.add(reply_msg)
                    await db2.commit()
                return

            event_data = json.dumps({**result, "intent": intent}, ensure_ascii=False)
            yield f"data: {event_data}\n\n"
            yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id})}\n\n"
            return
        # === 表单引擎结束 ===

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
                    tenant_id=tenant_id,
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
        system_content = _load_business_prompt(tenant_id)
        # 需要注入 RAG 知识的意图集合（电商 + 物业等通用场景）
        _rag_intents = {"price", "default", "fee", "repair", "complain", "notice"}
        if intent in _rag_intents:
            # 短消息/问候类跳过RAG，避免检索毒化上下文
            greeting_patterns = ["您好", "你好", "在吗", "嗨", "哈喽", "早上好", "下午好", "晚上好"]
            is_greeting = len(original_message.strip()) <= 5 or any(g in original_message for g in greeting_patterns)
            if is_greeting:
                results = []
            else:
                results = await retriever.retrieve(original_message, top_k=3, tenant_id=tenant_id)
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

        if intent == "after_sale":
            stream = agent.chat_stream(msgs, order_no=order_no, tenant_id=tenant_id)
        elif intent in _rag_intents:
            stream = agent.llm.chat_stream(msgs)
        elif intent == "tech":
            stream = agent.chat_stream(msgs, tenant_id=tenant_id)
        elif intent == "logistics":
            stream = agent.chat_stream(msgs, order_no=order_no, tenant_id=tenant_id)
        else:
            stream = agent.llm.chat_stream(msgs)
        retrieval_results = []
        async for token in stream:
            if token == "[DONE]":
                break
            if token.startswith("__retrieval__:"):
                try:
                    retrieval_results = json.loads(token[len("__retrieval__:"):])
                except Exception:
                    pass
                continue
            # 富交互卡片：非token的JSON对象直接当SSE事件转发
            if token.startswith("{") and '"type"' in token:
                yield f"data: {token}\n\n"
                continue
            token = filter_output(token)
            full_reply += token
            if not SHADOW_MODE:
                yield f"data: {json.dumps({'token': token, 'intent': intent})}\n\n"

        full_reply = filter_output(full_reply)

        if intent in _rag_intents:
            retrieval_results = [{"text": r["text"], "score": r.get("score", 0)} for r in results]

        quality = _quality_check(full_reply, retrieval_results)
        extra_meta = {"intent": intent, "shadow": SHADOW_MODE}
        if retrieval_results:
            extra_meta["retrieval_results"] = retrieval_results
        if quality:
            extra_meta.update(quality)

        async with async_session() as db:
            reply_msg = Message(
                session_id=sess.id,
                role="assistant",
                content=full_reply,
                content_type="text",
                extra_metadata=extra_meta,
                tenant_id=tenant_id,
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

        yield f"data: {json.dumps({'done': True, 'intent': intent, 'session_id': sess.id, 'message_id': str(reply_msg.id), 'shadow': SHADOW_MODE})}\n\n"
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


@router.post("/api/messages/{message_id}/feedback")
async def message_feedback(message_id: str, feedback: str = "thumbs_up"):
    """记录用户对助手消息的反馈（点赞/踩）"""
    if feedback not in ("thumbs_up", "thumbs_down"):
        raise HTTPException(status_code=400, detail="feedback must be thumbs_up or thumbs_down")
    async with async_session() as db:
        result = await db.execute(select(Message).where(Message.id == message_id))
        msg = result.scalar_one_or_none()
        if not msg:
            raise HTTPException(status_code=404, detail="message not found")
        if msg.extra_metadata is None:
            msg.extra_metadata = {}
        msg.extra_metadata["user_feedback"] = feedback
        if feedback == "thumbs_down":
            msg.extra_metadata["quality_flag"] = "user_reported"
        db.add(msg)
        await db.commit()
    return {"status": "ok", "message_id": message_id, "feedback": feedback}
