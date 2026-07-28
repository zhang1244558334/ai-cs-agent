from .base_agent import BaseAgent


class DefaultAgent(BaseAgent):
    def _build_messages(
        self, user_msg: str, context: list, extra_context: dict
    ) -> list:
        system = {
            "role": "system",
            "content": "你是智能客服助手。如果是电商相关问题，友好解答。如果是其他问题（天气、问候、闲聊等），也可以正常回答，保持简洁。不超过50字。",
        }
        return [system] + context + [{"role": "user", "content": user_msg}]
