import logging
import time

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    async def chat(self, messages: list, temperature: float | None = None) -> str:
        last_error = None
        for attempt, delay in [(1, 0), (2, 2), (3, 4)]:
            try:
                resp = await self.client.chat.completions.create(
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
        try:
            resp = await self.client.chat.completions.create(
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
        except Exception as e:
            logger.error(f"LLM stream failed: {e}")
            yield "[DONE]"
