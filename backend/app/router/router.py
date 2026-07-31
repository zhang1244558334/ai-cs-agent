from ..agents.langgraph_flows.complaint_flow import complaint_graph
from .intent_vector_matcher import IntentVectorMatcher
from .keyword_matcher import KeywordMatcher
from .llm_classifier import LLMClassifier
from .regex_matcher import RegexMatcher


class Router:
    def __init__(self):
        self.keyword_matcher = KeywordMatcher()
        self.regex_matcher = RegexMatcher()
        self.intent_vector = IntentVectorMatcher()
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
        vec = self.intent_vector.query(text)
        if vec:
            return vec[0]
        return await self.llm_classifier.classify(text)

    async def route_with_graph(
        self, text: str, session_id: str = ""
    ) -> tuple[str, str | None]:
        intent = await self.route(text)
        if intent == "after_sale":
            complaint_kw = ["投诉", "举报", "商家不处理", "一直不退", "不给退", "态度差", "欺骗"]
            if any(kw in text for kw in complaint_kw):
                return "complaint", session_id
        return intent, None
