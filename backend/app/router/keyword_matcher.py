import yaml


class KeywordMatcher:
    def __init__(self, rules_path="config/router_rules.yaml"):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)["intents"]
        self._exit_words = ["退出", "取消", "不要", "不用", "不需要", "停止"]

    def match(self, text: str) -> str | None:
        text_lower = text.lower()
        for intent, cfg in self.rules.items():
            for kw in cfg.get("keywords", []):
                if kw in text_lower:
                    if intent == "handover":
                        # 同时有退出词 → 不是真的想转人工
                        if any(w in text_lower for w in self._exit_words):
                            return None
                    return intent
        return None
