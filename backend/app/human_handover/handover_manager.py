from datetime import datetime

from sqlalchemy import text

from app.core.database import async_session
from app.models.handover_log import HandoverLog
from app.models.session import Session

DEFAULT_TIMEOUT = 3600


class HandoverManager:
    async def check_handover_request(self, text: str) -> bool:
        keywords = ["人工", "转人工", "客服", "真人", "投诉"]
        for kw in keywords:
            if kw in text:
                return True
        return False

    async def switch_to_human(
        self, session_id: str, reason: str = "user_requested"
    ):
        async with async_session() as db:
            sess = await db.get(Session, session_id)
            if sess:
                old_mode = sess.mode
                sess.mode = "human"
                log = HandoverLog(
                    session_id=session_id,
                    switched_by="user",
                    from_mode=old_mode,
                    to_mode="human",
                    reason=reason,
                )
                db.add(log)
                await db.commit()

    async def check_timeout_human(
        self, session_id: str, timeout: int = DEFAULT_TIMEOUT
    ) -> bool:
        async with async_session() as db:
            log = (
                await db.execute(
                    text(
                        "SELECT created_at FROM handover_logs "
                        "WHERE session_id=:sid AND to_mode='human' "
                        "ORDER BY created_at DESC LIMIT 1"
                    ),
                    {"sid": session_id},
                )
            ).fetchone()
            if log:
                created_at_str = str(log[0])
                created_at = datetime.strptime(
                    created_at_str.split(".")[0], "%Y-%m-%d %H:%M:%S"
                )
                elapsed = (datetime.utcnow() - created_at).total_seconds()
                if elapsed > timeout:
                    sess = await db.get(Session, session_id)
                    if sess and sess.mode == "human":
                        sess.mode = "ai"
                        log2 = HandoverLog(
                            session_id=session_id,
                            switched_by="timeout",
                            from_mode="human",
                            to_mode="ai",
                            reason="auto_back",
                        )
                        db.add(log2)
                        await db.commit()
                    return True
            return False
