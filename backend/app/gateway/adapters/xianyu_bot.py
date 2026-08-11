"""
闲鱼智能客服机器人。
基于 XianyuLive WebSocket，监听消息并调用 AI 引擎自动回复。
"""
import asyncio
import json
import sys
import os
import base64
import re
import threading

# 确保 SDK 可导入
_sdk = os.path.join(os.path.dirname(__file__), "..", "..", "platforms", "xianyu_sdk")
if _sdk not in sys.path:
    sys.path.insert(0, _sdk)

from goofish_live import XianyuLive
from message import make_text


class XianyuBot(XianyuLive):
    """闲鱼AI客服机器人。"""

    FALLBACK_REPLY = "抱歉，暂时无法处理您的消息，请稍后再试或联系卖家"

    def __init__(self, cookies_str: str):
        super().__init__(cookies_str)
        self._router = None
        self._agent = None
        self._lock = asyncio.Lock()
        self._pending: dict = {}
        self._replied_ids: set = set()
        self._known_cids: dict = {}  # cid → user_id，用于重连后消息补拉
        self._item_cache: dict = {}  # item_id → raw_itemDO dict，避免重复调API
        self._reconnect_count: int = 0  # 连续重连失败计数，用于Cookie过期检测

    def _init_ai(self):
        if self._router is None:
            from app.router.router import Router
            from app.agents.default_agent import DefaultAgent
            self._router = Router()
            self._agent = DefaultAgent()

    async def main(self):
        from utils.goofish_utils import get_session_cookies_str, generate_mid
        import websockets

        threading.Thread(target=self.user_alive).start()

        while True:
            try:
                headers = {
                    "Cookie": get_session_cookies_str(self.xianyu.session),
                    "Host": "wss-goofish.dingtalk.com",
                    "Connection": "Upgrade",
                    "Pragma": "no-cache",
                    "Cache-Control": "no-cache",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Origin": "https://www.goofish.com",
                    "Accept-Encoding": "gzip, deflate, br, zstd",
                    "Accept-Language": "zh-CN,zh;q=0.9",
                }
                async with websockets.connect(self.base_url, additional_headers=headers) as ws:
                    asyncio.create_task(self.init(ws))
                    asyncio.create_task(self.heart_beat(ws))
                    print("[XianyuBot] 已连接")
                    self._reconnect_count = 0  # 连接成功后重置重连计数
                    self._replied_ids.clear()  # 清空去重集合，避免旧msg_id阻塞
                    # 重连后补拉消息：3秒断开间隙可能丢失推送，对所有已知会话拉取最新消息
                    for cid, user_id in list(self._known_cids.items()):
                        send_mid = generate_mid()
                        req = {
                            "lwp": "/r/MessageManager/listUserMessages",
                            "headers": {"mid": send_mid},
                            "body": [f"{cid}@goofish", False, 9007199254740991, 5, False],
                        }
                        fut = asyncio.get_event_loop().create_future()
                        self._pending[send_mid] = (fut, cid, user_id)
                        await ws.send(json.dumps(req))
                        await asyncio.sleep(0.3)  # 避免服务器限流
                    async for raw in ws:
                        msg = json.loads(raw)
                        ack = {
                            "code": 200,
                            "headers": {
                                "mid": msg.get("headers", {}).get("mid", generate_mid()),
                                "sid": msg.get("headers", {}).get("sid", ""),
                            },
                        }
                        for key in ("app-key", "ua", "dt"):
                            if key in msg.get("headers", {}):
                                ack["headers"][key] = msg["headers"][key]
                        await ws.send(json.dumps(ack))

                        mid = msg.get("headers", {}).get("mid", "")
                        async with self._lock:
                            in_pending = mid in self._pending
                        if in_pending:
                            await self._on_list_response(mid, msg, ws)
                            continue
                        await self._on_push(msg, ws)
            except Exception as e:
                self._reconnect_count += 1
                print(f"[XianyuBot] 断开，3秒后重连: {e}（第{self._reconnect_count}次）")
                if self._reconnect_count >= 3:
                    print(f"⚠️ 连续重连失败{self._reconnect_count}次，Cookie可能已过期。请浏览器打开goofish.com → F12 → Application → Cookies → 复制所有cookie → 替换config/settings.json中的app_key → 重启服务")
                await asyncio.sleep(3)

    async def _on_push(self, msg, ws):
        data = None
        try:
            data = msg["body"]["syncPushPackage"]["data"][0]["data"]
            # 尝试直接解析JSON，如果成功说明是明文推送
            parsed = json.loads(data)
            # 明文格式尝试提取cid/user_id
            if isinstance(parsed, dict):
                cid = parsed.get("cid", "") or parsed.get("targetId", "")
                user_id = parsed.get("fromUserId", "") or parsed.get("from", "")
                if not cid:
                    # 尝试嵌套结构
                    for key in parsed:
                        if isinstance(parsed[key], dict):
                            cid = parsed[key].get("cid", "") or cid
                            user_id = parsed[key].get("fromUserId", "") or user_id
                if cid and "@" in str(cid):
                    cid = cid.split("@")[0]
                if user_id and "@" in str(user_id):
                    user_id = user_id.split("@")[0]
                if cid and user_id:
                    self._known_cids[cid] = user_id
                    print(f"[XianyuBot] 收到推送 cid={cid} user={user_id}")
                    from utils.goofish_utils import generate_mid
                    send_mid = generate_mid()
                    req = {
                        "lwp": "/r/MessageManager/listUserMessages",
                        "headers": {"mid": send_mid},
                        "body": [f"{cid}@goofish", False, 9007199254740991, 5, False],
                    }
                    fut = asyncio.get_event_loop().create_future()
                    async with self._lock:
                        self._pending[send_mid] = (fut, cid, user_id)
                    await ws.send(json.dumps(req))
                    return
        except Exception:
            if data is None:
                return
            try:
                from utils.goofish_utils import decrypt
                data = decrypt(data)
                parsed = json.loads(data)
                if isinstance(parsed.get("1"), list) and len(parsed["1"]) > 0:
                    item = parsed["1"][0]
                    cid = item.get("1", "").split("@")[0]
                    user_id = item.get("4", "").split("@")[0]
                    if not cid or not user_id:
                        return
                    self._known_cids[cid] = user_id
                    print(f"[XianyuBot] 收到推送 cid={cid} user={user_id}")
                    from utils.goofish_utils import generate_mid
                    send_mid = generate_mid()
                    req = {
                        "lwp": "/r/MessageManager/listUserMessages",
                        "headers": {"mid": send_mid},
                        "body": [f"{cid}@goofish", False, 9007199254740991, 5, False],
                    }
                    fut = asyncio.get_event_loop().create_future()
                    async with self._lock:
                        self._pending[send_mid] = (fut, cid, user_id)
                    await ws.send(json.dumps(req))
            except Exception as e:
                pass  # 忽略解密失败的消息

    def _extract_item_id(self, body: dict) -> str:
        """从消息数据中提取商品ID"""
        for um in body.get("userMessageModels", []):
            ext = um.get("message", {}).get("extension", {})
            url = ext.get("reminderUrl", "")
            m = re.search(r"itemId=(\d+)", url)
            if m:
                return m.group(1)
        return ""

    def _fetch_item_info(self, item_id: str) -> str:
        """调用闲鱼API获取商品详情（返回格式化文本）"""
        _, text = self._fetch_item_info_full(item_id)
        return text

    def _fetch_item_info_raw(self, item_id: str) -> dict:
        """调用闲鱼API获取商品详情（返回原始字典 itemDO）"""
        raw, _ = self._fetch_item_info_full(item_id)
        return raw

    def _fetch_item_info_full(self, item_id: str) -> tuple:
        """调用闲鱼API获取商品详情，返回 (raw_itemDO_dict, formatted_text)"""
        try:
            # 优先从缓存读取，避免重复调API被限流
            if item_id in self._item_cache:
                item = self._item_cache[item_id]
                print(f"[XianyuBot] _fetch_item_info_full: item_id={item_id} 命中缓存, "
                      f"keys={list(item.keys()) if item else 'EMPTY_CACHED'}")
            else:
                print(f"[XianyuBot] _fetch_item_info_full: item_id={item_id} 未命中缓存, 调用API...")
                # 诊断 session cookies 状态
                try:
                    m_h5_tk = self.xianyu.session.cookies.get('_m_h5_tk', 'MISSING')
                    cookie_count = len(self.xianyu.session.cookies)
                    print(f"[XianyuBot] _fetch_item_info_full: cookies总数={cookie_count}, _m_h5_tk={'有' if m_h5_tk != 'MISSING' else '缺失!'}")
                except Exception:
                    print(f"[XianyuBot] _fetch_item_info_full: 无法读取cookies状态")
                info = self.xianyu.get_item_info(item_id)
                # 打印API返回顶层keys用于诊断
                top_keys = list(info.keys()) if isinstance(info, dict) else type(info).__name__
                data_keys = list(info.get("data", {}).keys()) if isinstance(info.get("data"), dict) else "N/A"
                print(f"[XianyuBot] _fetch_item_info_full: API返回顶层keys={top_keys}, data子keys={data_keys}")
                # 数据结构: data.itemDO.{title, soldPrice, desc, itemStatusStr}
                item = info.get("data", {}).get("itemDO", {})
                if item:
                    self._item_cache[item_id] = item
                    print(f"[XianyuBot] _fetch_item_info_full: itemDO非空, keys={list(item.keys())}, 已缓存")
                else:
                    print(f"[XianyuBot] _fetch_item_info_full: itemDO为空或不存在! "
                          f"info['data']={json.dumps(info.get('data'), ensure_ascii=False)[:300] if 'data' in info else 'NO_DATA_KEY'}")

            # formatted_text 每次都要重新生成（不同场景可能需要不同格式）
            title = item.get("title", "")
            price = item.get("soldPrice", "")
            desc = item.get("desc", "")
            status = item.get("itemStatusStr", "")
            category = ""
            labels = item.get("itemLabelExtList", [])
            if labels:
                category = labels[0].get("valueText", "")
            parts = []
            if title:
                parts.append(f"商品标题：{title}")
            if price:
                parts.append(f"价格：¥{price}")
            if category:
                parts.append(f"分类：{category}")
            if status:
                parts.append(f"状态：{status}")
            if desc:
                parts.append(f"描述：{desc[:200]}")
            text = "\n".join(parts) if parts else ""
            return item, text
        except Exception as e:
            import traceback
            print(f"[XianyuBot] _fetch_item_info_full 异常: {e}")
            traceback.print_exc()
            return {}, ""

    async def _on_list_response(self, mid, msg, ws):
        async with self._lock:
            fut, cid, user_id = self._pending.pop(mid)
        body = msg.get("body", {})

        # 提取商品ID
        item_id = self._extract_item_id(body)

        # 将商品信息灌入ChromaDB知识库（不阻塞主流程）
        if item_id:
            try:
                # 在executor中运行同步API调用，避免阻塞事件循环
                loop = asyncio.get_running_loop()
                raw_item = await loop.run_in_executor(None, self._fetch_item_info_raw, item_id)
                if raw_item:
                    from app.knowledge.product_indexer import ProductIndexer
                    ProductIndexer().index_item(item_id, raw_item)
                else:
                    cached = item_id in self._item_cache
                    print(f"[XianyuBot] 商品索引跳过: item_id={item_id}, "
                          f"原因=_fetch_item_info_raw返回空dict, "
                          f"是否命中缓存={cached}, "
                          f"提取URL中的itemId={item_id}")
            except Exception as e:
                import traceback
                print(f"[XianyuBot] 商品索引异常: item_id={item_id}, error={e}")
                traceback.print_exc()

        # 遍历所有对方消息，逐一回复（去重由 _do_reply 中的 _replied_ids 处理）
        for um in body.get("userMessageModels", []):
            ext = um.get("message", {}).get("extension", {})
            sender_id = ext.get("senderUserId", "")
            if sender_id == self.myid:
                continue

            content_data = (
                um.get("message", {}).get("content", {}).get("custom", {}).get("data", "")
            )
            msg_text = ""
            if content_data:
                try:
                    decoded = json.loads(base64.b64decode(content_data).decode("utf-8"))
                    if decoded.get("contentType") == 1:
                        msg_text = decoded.get("text", {}).get("text", "")
                except Exception:
                    pass

            user_name = ext.get("reminderTitle", "")
            user_msg = msg_text or ext.get("reminderContent", "")

            if not user_msg:
                continue

            # 从extension.extJson中提取messageId用于去重
            msg_id = ""
            try:
                ext_json_str = um.get("message", {}).get("extension", {}).get("extJson", "")
                if ext_json_str:
                    ext_json = json.loads(ext_json_str)
                    msg_id = ext_json.get("messageId", "")
            except Exception:
                pass

            print(f"[XianyuBot] {user_name}: {user_msg}")
            asyncio.create_task(self._do_reply(ws, cid, user_id, user_name, user_msg, item_id, mid, msg_id))

        fut.set_result(None)

    async def _do_reply(self, ws, cid, user_id, user_name, user_msg, item_id, req_mid, msg_id=""):
        """AI生成回复+发送+落库 — 按意图调度专业Agent"""
        async with self._lock:
            if msg_id and msg_id in self._replied_ids:
                print(f"[XianyuBot] 跳过重复 msg_id={msg_id}: {user_msg[:30]}")
                return
            if msg_id:
                self._replied_ids.add(msg_id)
                # LRU: 保留最近1000条
                if len(self._replied_ids) > 1000:
                    self._replied_ids.clear()

        self._init_ai()

        # 表单引擎 & 统一回复生成
        try:
            intent = await self._router.route(user_msg, tenant_id="xianyu")
            print(f"[XianyuBot] 意图: {intent}")

            # no_reply 在闲鱼转闲聊，直接调LLM自由发挥（generate_reply内部会重新路由又判no_reply）
            if intent == "no_reply":
                self._init_ai()
                reply = await self._agent.llm.chat([
                    {"role": "system", "content": "你是闲鱼卖家，跟买家闲聊。回复随意口语化，不超过30字。买家开玩笑就配合着玩。"},
                    {"role": "user", "content": user_msg},
                ])
                print(f"[XianyuBot] AI(闲聊): {reply}")
                await self.send_msg(ws, cid, user_id, make_text(reply))
                await self._save_message(user_id, user_name, user_msg, reply, "default")
                return

            # after_sale意图：仅当有行动词+订单号时才进表单，纯政策咨询走RAG回答
            _is_policy_question = False
            if intent == "after_sale":
                _action_kw = ["帮我退", "我要退", "申请退货", "退货退款", "退款"]
                _has_action = any(kw in user_msg for kw in _action_kw)
                _has_order = bool(re.search(r"(MOCK\d+|\d{8,})", user_msg))
                if not _has_action and not _has_order:
                    _is_policy_question = True
                    print(f"[XianyuBot] 政策咨询，跳过表单", flush=True)

            # 多轮表单引擎（售后/退换货等）— 政策咨询跳过
            if not _is_policy_question:
                form_result = await self._handle_form(user_id, user_msg, intent)
                if form_result:
                    reply_text = form_result["reply"]
                    await self.send_msg(ws, cid, user_id, make_text(reply_text))
                    await self._save_message(user_id, user_name, user_msg, reply_text, intent)
                    print(f"[XianyuBot] 表单: {reply_text[:50]}")
                    return

            # 商品信息
            item_info = self._fetch_item_info(item_id) if item_id else ""

            # 复用主流程统一的 generate_reply
            from app.api.routes.chat import generate_reply
            result = await generate_reply(user_msg, user_id, "xianyu", item_info)
            reply = result["reply"]
            intent = result["intent"]

            print(f"[XianyuBot] AI: {reply}")

            await self.send_msg(ws, cid, user_id, make_text(reply))
            print("[XianyuBot] 已回复")

            await self._save_message(user_id, user_name, user_msg, reply, intent)

        except Exception as e:
            import traceback
            print(f"[XianyuBot] _do_reply 异常，使用兜底回复: {e}")
            traceback.print_exc()
            # 清理msg_id，避免重连后永久跳过
            if msg_id:
                async with self._lock:
                    self._replied_ids.discard(msg_id)
            reply = self.FALLBACK_REPLY
            # 尝试发送兜底回复
            try:
                await self.send_msg(ws, cid, user_id, make_text(reply))
                print("[XianyuBot] 兜底回复已发送")
            except Exception as e2:
                print(f"[XianyuBot] 兜底回复发送失败(WS可能已断): {e2}")
            # 兜底回复也要落库
            try:
                await self._save_message(user_id, user_name, user_msg, reply, "fallback")
            except Exception as e3:
                print(f"[XianyuBot] 兜底回复落库失败: {e3}")

    async def _handle_form(self, user_id: str, user_msg: str, intent: str) -> dict | None:
        """多轮表单引擎：售后/退换货等需要收集信息的场景"""
        from app.forms.engine import FormEngine
        from app.core.database import async_session as _as
        from app.models.session import Session as Sess
        from sqlalchemy import select as _sel

        form_engine = FormEngine()

        # 加载session获取form_state
        async with _as() as db:
            result = await db.execute(
                _sel(Sess).where(Sess.platform == "xianyu", Sess.platform_session_id == user_id)
            )
            sess_obj = result.scalar_one_or_none()

        form_state = sess_obj.extra_metadata.get("form_state") if (sess_obj and sess_obj.extra_metadata) else None
        form_intents = form_engine.get_form_intents("xianyu")

        # 取消命令
        if form_state and any(w in user_msg for w in ["取消", "算了", "不用了", "不想", "不退了", "不弄了"]):
            sess_obj.extra_metadata["form_state"] = None
            async with _as() as db:
                await db.merge(sess_obj)
                await db.commit()
            return {"reply": "已取消当前操作，有什么可以帮您的？"}

        # 表单进行中
        if form_state and form_state.get("status") in ("collecting", "confirming"):
            result_data = form_engine.process(user_msg, form_state, form_state["intent"], "xianyu")

            if result_data["type"] == "form_slot":
                reply = result_data["prompt"]
            elif result_data["type"] == "form_confirm":
                reply = result_data["summary"] + "\n确认无误请回复\"确认\"，需要修改请回复\"修改\""
            elif result_data["type"] == "form_done":
                reply = result_data["result"]
                form_state["status"] = "done"
            else:
                reply = result_data.get("prompt", "请继续操作")

            # 保存form_state
            sess_obj.extra_metadata["form_state"] = form_state
            async with _as() as db:
                await db.merge(sess_obj)
                await db.commit()

            return {"reply": reply}

        # 新表单：意图匹配表单模板
        if intent in form_intents and not form_state:
            form_state, first_prompt = form_engine.start(intent, "xianyu", trigger_message=user_msg)
            if form_state and first_prompt:
                # 保存form_state到session
                if not sess_obj:
                    import uuid as _uuid
                    sess_obj = Sess(
                        id=str(_uuid.uuid4()), platform="xianyu",
                        platform_session_id=user_id, user_id="",
                        tenant_id="ecommerce", extra_metadata={"form_state": form_state},
                    )
                    async with _as() as db:
                        db.add(sess_obj)
                        await db.commit()
                else:
                    sess_obj.extra_metadata["form_state"] = form_state
                    async with _as() as db:
                        await db.merge(sess_obj)
                        await db.commit()
                return {"reply": first_prompt}

        return None

    async def _save_message(self, user_id: str, user_name: str, user_msg: str, reply: str, intent: str):
        """落库"""
        try:
            from app.core.database import async_session as _as
            from app.models.message import Message
            from app.models.session import Session as Sess
            from sqlalchemy import select as _sel
            import uuid as _uuid

            async with _as() as db:
                result = await db.execute(
                    _sel(Sess).where(Sess.platform == "xianyu", Sess.platform_session_id == user_id)
                )
                sess_obj = result.scalar_one_or_none()
                if not sess_obj:
                    sess_obj = Sess(
                        id=str(_uuid.uuid4()), platform="xianyu",
                        platform_session_id=user_id, user_id=user_name,
                        tenant_id="xianyu", extra_metadata={"form_state": None},
                    )
                    db.add(sess_obj)
                    await db.flush()

                db.add(Message(session_id=sess_obj.id, role="user", content=user_msg,
                               content_type="text", tenant_id="ecommerce"))
                db.add(Message(session_id=sess_obj.id, role="assistant", content=reply,
                               content_type="text", tenant_id="ecommerce",
                               extra_metadata={"intent": intent, "platform": "xianyu"}))
                await db.commit()
            print("[XianyuBot] 已落库")
        except Exception as e:
            print(f"[XianyuBot] 落库失败: {e}")

    async def _load_history(self, user_id: str) -> list:
        """加载对话历史（仅用户消息）"""
        history = []
        try:
            from app.core.database import async_session as _as
            from app.models.message import Message
            from app.models.session import Session as Sess
            from sqlalchemy import select as _sel

            async with _as() as db:
                result = await db.execute(
                    _sel(Sess).where(Sess.platform == "xianyu", Sess.platform_session_id == user_id)
                )
                sess_obj = result.scalar_one_or_none()
                if sess_obj:
                    result = await db.execute(
                        _sel(Message).where(Message.session_id == sess_obj.id)
                        .order_by(Message.created_at.desc()).limit(10)
                    )
                    for row in reversed(list(result.scalars().all())):
                        if row.role == "user":
                            history.append(row.content)
        except Exception:
            pass
        return history

    async def _rewrite_query(self, user_msg: str, history: list) -> str:
        """Query重写：把"那个呢"等残缺提问补全"""
        if len(user_msg) > 15 or not history:
            return ""  # 完整句子不需要重写

        self._init_ai()
        ctx = " | ".join(history[-3:]) if history else "无历史"
        try:
            rewritten = await self._agent.llm.chat([
                {"role": "system", "content": (
                    "你是购物用户，正在和客服对话。根据对话历史，把你刚说的这句话"
                    "补全成完整问句。如果是完整句子就原样输出。只输出补全后的句子。"
                )},
                {"role": "user", "content": f"对话历史：{ctx}\n当前消息：{user_msg}"},
            ])
            if rewritten and 3 < len(rewritten.strip()) < 200:
                return rewritten.strip()
        except Exception:
            pass
        return ""

    async def _build_context(self, user_id: str, user_msg: str, item_id: str) -> str:
        """构建回复上下文：业务prompt + 商品信息 + 知识库 + 历史"""
        import os as _os, json as _json

        # 1. 业务prompt
        biz_prompt = "你是闲鱼卖家客服助手，请友好简洁地回复。"
        biz_path = _os.path.join(
            _os.path.dirname(__file__), "..", "..", "..", "data", "businesses.json"
        )
        try:
            with open(biz_path, "r", encoding="utf-8") as f:
                for b in _json.load(f):
                    if b.get("id") == "xianyu" and b.get("prompt"):
                        biz_prompt = b["prompt"]
        except Exception:
            pass

        # 2. 商品信息（从闲鱼API）
        item_info = ""
        if item_id:
            item_info = self._fetch_item_info(item_id)
            if item_info:
                print(f"[XianyuBot] 商品信息: {item_info[:100]}...")

        # 3. RAG知识库
        rag_text = ""
        try:
            from app.knowledge.retriever import Retriever
            retriever = Retriever()
            rag_results = await retriever.retrieve(user_msg, tenant_id="xianyu", top_k=2)
            rag_text = "\n".join(r.get("text", "") for r in rag_results if r.get("text"))
        except Exception:
            pass

        # 4. 组装system prompt
        parts = [biz_prompt]
        if item_info:
            parts.append(f"\n当前买家咨询的商品：\n{item_info}")
        if rag_text:
            parts.append(f"\n知识库参考：\n{rag_text}")
        parts.append(
            "\n回复规则："
            "\n1. 先判断买家是在正经询问还是闲聊/开玩笑"
            "\n2. 开玩笑就幽默回应，闲聊就自然地聊，不用每句都扯回商品"
            "\n3. 正经问题时问什么答什么，不主动推销"
            "\n4. 语气随意口语化，像微信聊天"
            "\n5. 不重复说过的话，尽量30字内"
        )

        return "\n".join(parts)

    async def start_bot(self):
        print("[XianyuBot] 正在连接闲鱼...")
        await self.main()


async def run_xianyu_bot(cookies_str: str):
    bot = XianyuBot(cookies_str)
    await bot.start_bot()
