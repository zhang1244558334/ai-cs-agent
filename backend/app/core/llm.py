import logging
import time

from openai import AsyncOpenAI

from app.core.config import settings as app_settings

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM客户端，每次调用时从全局settings动态读取api_key/base_url/model，
    支持运行时热切换配置而无需重建Agent。"""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        # 初始值仅用于fallback；每次调用从app_settings读取最新值
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._last_key = None
        self._client = None

    def _get_client(self):
        key = app_settings.llm_api_key or self._api_key or ""
        if key != self._last_key:
            base = app_settings.llm_base_url or self._base_url or "https://api.openai.com/v1"
            self._client = AsyncOpenAI(api_key=key, base_url=base)
            self._last_key = key
        return self._client

    @property
    def model(self):
        return app_settings.llm_model or self._model or "gpt-4o-mini"

    async def chat(self, messages: list, temperature: float | None = None) -> str:
        last_error = None
        for attempt, delay in [(1, 0), (2, 2), (3, 4)]:
            try:
                resp = await self._get_client().chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=30,
                )
                return resp.choices[0].message.content
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call attempt {attempt} failed: {e}")
                if delay:
                    time.sleep(delay)
        logger.error(f"LLM call failed after 3 attempts: {last_error}")
        return "抱歉，我现在处理不过来，请稍后再试。"

    async def chat_stream(
        self, messages: list, temperature: float | None = None
    ):
        last_error = None
        for attempt, delay in [(1, 0), (2, 2), (3, 4)]:
            try:
                resp = await self._get_client().chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature or self.temperature,
                    max_tokens=self.max_tokens,
                    timeout=30,
                    stream=True,
                )
                async for chunk in resp:
                    delta = chunk.choices[0].delta if chunk.choices else None
                    if delta and delta.content:
                        yield delta.content
                yield "[DONE]"
                return
            except Exception as e:
                last_error = e
                logger.warning(f"LLM stream attempt {attempt} failed: {e}")
                if delay:
                    time.sleep(delay)
        logger.error(f"LLM stream failed after 3 attempts: {last_error}")
        yield "抱歉，我现在处理不过来，请稍后再试。"
        yield "[DONE]"
