from ..agents.langgraph_flows.complaint_flow import complaint_graph
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

    async def route_with_graph(
        self, text: str, session_id: str = ""
    ) -> tuple[str, str | None]:
        intent = await self.route(text)
        if intent == "after_sale":
            complaint_kw = ["投诉", "退货", "退款"]
            if any(kw in text for kw in complaint_kw):
                return "complaint", session_id
        return intent, None
