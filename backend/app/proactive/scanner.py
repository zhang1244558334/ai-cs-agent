import asyncio
import json
import os
from datetime import datetime

from sqlalchemy import select

from app.agents.proactive_agent import ProactiveAgent
from app.core.database import async_session
from app.models.message import Message
from app.models.proactive_log import ProactiveLog
from app.models.session import Session
from app.proactive.user_state import UserStateManager

EVENTS_FILE = "data/events.json"
POLL_INTERVAL = 60


class ProactiveScanner:
    def __init__(self):
        self._task = None
        self._user_state = UserStateManager()

    async def start(self):
        loop = asyncio.get_running_loop()
        self._task = loop.create_task(self._loop())
        print("[ProactiveScanner] started")

    async def stop(self):
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self):
        tick = 0
        while True:
            try:
                await self.scan()
            except Exception as e:
                print(f"[ProactiveScanner] scan error: {e}")
            # 每30分钟自动归因分析
            tick += 1
            if tick % 30 == 0:
                try:
                    from app.attribution.engine import AttributionEngine
                    engine = AttributionEngine()
                    n1 = await engine.analyze_flagged_messages()
                    n2 = await engine.analyze_batch()
                    print(f"[ProactiveScanner] attribution: flagged={n1} handover={n2}")
                except Exception as e:
                    print(f"[ProactiveScanner] attribution error: {e}")
            await asyncio.sleep(POLL_INTERVAL)

    async def scan(self):
        if not os.path.isfile(EVENTS_FILE):
            return
        with open(EVENTS_FILE, encoding="utf-8") as f:
            events = json.load(f)

        pending = [e for e in events if e.get("status") == "pending"]
        if not pending:
            return

        agent = ProactiveAgent()

        for event in pending:
            user_id = event.get("user_id", "")
            ok, reason = self._user_state.can_push(user_id)
            if not ok:
                print(f"[ProactiveScanner] skip {event['id']}: {reason}")
                continue

            content = await agent.generate(event)

            async with async_session() as db:
                # 已有同事件日志则跳过
                existing = await db.execute(
                    select(ProactiveLog).where(ProactiveLog.event_id == event["id"])
                )
                if existing.scalar_one_or_none():
                    continue

                # 写入主动服务日志
                log = ProactiveLog(
                    session_id=event.get("session_id", ""),
                    event_id=event["id"],
                    event_type=event.get("event_type", "unknown"),
                    push_content=content,
                )
                db.add(log)

                # 写入会话消息（让前端能看到）
                sess_id = event.get("session_id", "")
                if sess_id:
                    msg = Message(
                        session_id=sess_id,
                        role="assistant",
                        content=content,
                        content_type="text",
                        extra_metadata={"is_proactive": True, "event_type": event.get("event_type", "")},
                        tenant_id=event.get("tenant_id", "ecommerce"),
                    )
                    db.add(msg)
                await db.commit()

            self._user_state.record_push(user_id)
            print(f"[ProactiveScanner] pushed {event['id']} -> {user_id}")

        # 标记事件已推送
        for event in pending:
            event["status"] = "pushed"
        with open(EVENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(events, f, ensure_ascii=False, indent=2)
