import yaml


class KeywordMatcher:
    def __init__(self, rules_path="config/router_rules.yaml"):
        with open(rules_path) as f:
            self.rules = yaml.safe_load(f)["intents"]

    def match(self, text: str) -> str | None:
        text_lower = text.lower()
        for intent, cfg in self.rules.items():
            for kw in cfg.get("keywords", []):
                if kw in text_lower:
                    return intent
        return None
