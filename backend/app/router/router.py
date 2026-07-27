from .keyword_matcher import KeywordMatcher
from .llm_classifier import LLMClassifier
from .regex_matcher import RegexMatcher


class Router:
    def __init__(self):
        self.keyword_matcher = KeywordMatcher()
        self.regex_matcher = RegexMatcher()
        self.llm_classifier = LLMClassifier()

    async def route(self, text: str) -> str:
        kw = self.keyword_matcher.match(text)
        if kw == "handover":
            return "handover"
        if kw:
            return kw
        rx = self.regex_matcher.match(text)
        if rx:
            return rx
        return await self.llm_classifier.classify(text)
