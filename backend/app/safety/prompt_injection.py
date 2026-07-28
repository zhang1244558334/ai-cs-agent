INJECTION_KEYWORDS = [
    "你是什么模型",
    "忽略之前的指令",
    "你现在扮演",
    "请忘记",
    "系统指令",
]


def detect_injection(text: str) -> bool:
    text_lower = text.lower()
    for kw in INJECTION_KEYWORDS:
        if kw in text_lower:
            return True
    return False
