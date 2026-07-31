import json
import logging
from datetime import datetime


class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # 收集所有 extra 自定义字段
        for key in (
            "request_id",
            "session_id",
            "duration_ms",
            "tokens_used",
            "event",
            "intent",
            "platform_session_id",
            "message_preview",
            "reply_len",
        ):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)
        return json.dumps(log_entry, ensure_ascii=False)


def setup_logger(level: str = "INFO"):
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str):
    return logging.getLogger(name)
