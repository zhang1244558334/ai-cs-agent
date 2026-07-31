from app.core.config import settings
from app.core.llm import LLMClient


class ProactiveAgent:
    def __init__(self):
        self.llm = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.7,
            max_tokens=256,
        )

    async def generate(self, event: dict) -> str:
        messages = [
            {
                "role": "system",
                "content": "你是电商主动推送助手。根据用户事件生成简短友好的推送文案，不超过50字。",
            },
            {
                "role": "user",
                "content": (
                    f"事件类型:{event.get('event_type','')}\n"
                    f"事件数据:{event.get('data',{})}\n"
                    f"生成推送文案："
                ),
            },
        ]
        return await self.llm.chat(messages)
