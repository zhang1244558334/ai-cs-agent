from app.core.config import settings
from app.core.llm import LLMClient


class LLMClassifier:
    def __init__(self, llm_client=None):
        self.llm = llm_client or LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.3,
            max_tokens=50,
        )

    async def classify(self, text: str) -> str:
        if not text.strip():
            return "default"
        messages = [
            {
                "role": "system",
                "content": "你是一个客服意图分类器。只返回以下之一：price, tech, after_sale, handover, default, no_reply。不要解释。",
            },
            {"role": "user", "content": text},
        ]
        result = await self.llm.chat(messages)
        valid = ["price", "tech", "after_sale", "handover", "default", "no_reply"]
        for v in valid:
            if v in result.lower():
                return v
        return "default"
