from abc import ABC, abstractmethod

from app.core.config import settings
from app.core.llm import LLMClient


class BaseAgent(ABC):
    def __init__(self, llm_client: LLMClient | None = None):
        self.llm = llm_client or LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.4,
            max_tokens=1024,
        )

    async def generate(
        self,
        user_msg: str,
        context: list | None = None,
        extra_context: dict | None = None,
        temperature: float | None = None,
    ) -> str:
        messages = self._build_messages(
            user_msg, context or [], extra_context or {}
        )
        return await self._call_llm(messages, temperature)

    def _build_messages(
        self, user_msg: str, context: list, extra_context: dict
    ) -> list:
        return context + [{"role": "user", "content": user_msg}]

    async def _call_llm(
        self, messages: list, temperature: float | None = None
    ) -> str:
        return await self.llm.chat(messages, temperature)

    def _calc_confidence(self) -> float:
        return 0.8
