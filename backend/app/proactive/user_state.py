from datetime import datetime, time


class UserStateManager:
    def __init__(self, quiet_start: time | None = None, quiet_end: time | None = None):
        self.quiet_start = quiet_start or time(22, 0)
        self.quiet_end = quiet_end or time(8, 0)
        self._push_counts: dict[str, int] = {}
        self._last_push: dict[str, float] = {}

    def can_push(self, user_id: str) -> tuple[bool, str]:
        now = datetime.now().time()
        if self.quiet_start > self.quiet_end:
            # 跨天：22:00-08:00
            if now >= self.quiet_start or now < self.quiet_end:
                return False, "quiet_hours"
        else:
            if self.quiet_start <= now < self.quiet_end:
                return False, "quiet_hours"

        now_ts = datetime.now().timestamp()
        last_ts = self._last_push.get(user_id, 0)
        if now_ts - last_ts < 300:
            return False, "too_frequent"

        count = self._push_counts.get(user_id, 0)
        if count >= 3:
            return False, "daily_limit"

        return True, "ok"

    def record_push(self, user_id: str):
        self._last_push[user_id] = datetime.now().timestamp()
        self._push_counts[user_id] = self._push_counts.get(user_id, 0) + 1

    def reset_daily(self, user_id: str | None = None):
        if user_id:
            self._push_counts.pop(user_id, None)
        else:
            self._push_counts.clear()
