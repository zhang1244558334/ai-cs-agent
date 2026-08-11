import os

import yaml

# 非电商租户无专属规则时的最小规则集
_MINIMAL_RULES = {
    "handover": {"keywords": ["人工", "转人工", "真人"]},
    "no_reply": {"enable": True},
}


class KeywordMatcher:
    def __init__(self, default_rules_path="config/router_rules.yaml"):
        with open(default_rules_path) as f:
            self._default_rules = yaml.safe_load(f)["intents"]
        self._cache: dict[str, dict] = {}
        self._exit_words = ["退出", "取消", "不要", "不用", "不需要", "停止"]

    def _load_rules(self, tenant_id: str) -> dict:
        if tenant_id in self._cache:
            return self._cache[tenant_id]
        rules_path = os.path.join("config", "rules", tenant_id, "router_rules.yaml")
        if os.path.exists(rules_path):
            with open(rules_path) as f:
                rules = yaml.safe_load(f)["intents"]
        elif tenant_id == "ecommerce":
            rules = self._default_rules
        else:
            # 非电商租户无专属规则 → 最小规则集，避免电商意图泄漏
            rules = _MINIMAL_RULES
        self._cache[tenant_id] = rules
        return rules

    def match(self, text: str, tenant_id: str = "ecommerce") -> str | None:
        rules = self._load_rules(tenant_id)
        text_lower = text.lower()
        for intent, cfg in rules.items():
            for kw in cfg.get("keywords", []):
                if kw in text_lower:
                    if intent == "handover":
                        if any(w in text_lower for w in self._exit_words):
                            return None
                    return intent
        return None
