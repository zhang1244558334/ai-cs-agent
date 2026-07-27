import re

import yaml


class RegexMatcher:
    def __init__(self, rules_path="config/router_rules.yaml"):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)["intents"]

    def match(self, text: str) -> str | None:
        for intent, cfg in self.rules.items():
            for pattern in cfg.get("patterns", []):
                if re.search(pattern, text):
                    return intent
        return None
