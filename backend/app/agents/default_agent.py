from .base_agent import BaseAgent


class DefaultAgent(BaseAgent):
    def _build_messages(
        self, user_msg: str, context: list, extra_context: dict
    ) -> list:
        system = {
            "role": "system",
            "content": "你是电商客服助手。回复简洁友好，不超过50字。不知道的不要说。",
        }
        return [system] + context + [{"role": "user", "content": user_msg}]
