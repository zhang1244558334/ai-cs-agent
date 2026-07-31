from app.knowledge.retriever import Retriever

from .base_agent import BaseAgent


class TechAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.retriever = Retriever(alpha=0.7)

    async def generate(
        self,
        user_msg: str,
        context=None,
        extra_context=None,
        temperature=None,
    ):
        results = await self.retriever.retrieve(user_msg)
        knowledge = (
            "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"
        )
        system = {
            "role": "system",
            "content": (
                "你是产品技术客服。参考以下知识回答用户问题，"
                f"如果知识库没有答案请如实告知。\n\n参考知识：\n{knowledge}"
            ),
        }
        messages = [
            system,
            *(context or []),
            {"role": "user", "content": user_msg},
        ]
        return await self._call_llm(messages, temperature)

    async def chat_stream(self, messages: list):
        history = messages[:-1]
        user_msg = messages[-1]["content"] if messages else ""
        results = await self.retriever.retrieve(user_msg)
        knowledge = (
            "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"
        )
        system = {
            "role": "system",
            "content": (
                "你是产品技术客服。参考以下知识回答用户问题，"
                f"如果知识库没有答案请如实告知。\n\n参考知识：\n{knowledge}"
            ),
        }
        msgs = [system] + history + [{"role": "user", "content": user_msg}]
        async for token in self.llm.chat_stream(msgs):
            yield token
