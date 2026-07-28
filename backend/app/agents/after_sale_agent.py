from .base_agent import BaseAgent


class AfterSaleAgent(BaseAgent):
    def _build_messages(self, user_msg, context, extra_context):
        system = {
            "role": "system",
            "content": "你是售后客服助手。处理退换货/退款等问题。如果用户情绪激动或问题复杂，主动建议转人工。回复简洁不超过60字。",
        }
        return [system] + (context or []) + [{"role": "user", "content": user_msg}]
