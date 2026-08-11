import os
import re

import yaml

# 非电商租户无专属规则时的最小规则集
_MINIMAL_RULES = {
    "handover": {"keywords": ["人工", "转人工", "真人"]},
    "no_reply": {"enable": True},
}


class RegexMatcher:
    def __init__(self, default_rules_path="config/router_rules.yaml"):
        with open(default_rules_path) as f:
            self._default_rules = yaml.safe_load(f)["intents"]
        self._cache: dict[str, dict] = {}

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
            rules = _MINIMAL_RULES
        self._cache[tenant_id] = rules
        return rules

    def match(self, text: str, tenant_id: str = "ecommerce") -> str | None:
        rules = self._load_rules(tenant_id)
        for intent, cfg in rules.items():
            for pattern in cfg.get("patterns", []):
                if re.search(pattern, text):
                    return intent
        return None
