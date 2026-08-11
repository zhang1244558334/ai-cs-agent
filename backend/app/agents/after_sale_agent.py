import json
from app.core.config import settings
from app.knowledge.retriever import Retriever
from app.platforms.factory import PlatformGateway

from .base_agent import BaseAgent


class AfterSaleAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.retriever = Retriever(alpha=0.7)
        self.gateway = PlatformGateway()

    async def chat_stream(self, messages: list, order_no: str | None = None, tenant_id: str = "ecommerce"):
        history = messages[:-1]
        user_msg = messages[-1]["content"] if messages else ""

        results = await self.retriever.retrieve(user_msg, tenant_id=tenant_id)
        knowledge = "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"

        system_content = (
            "你是售后客服助手，负责处理退换货、退款、维修等问题。"
            "参考以下知识回答用户问题，如果知识库没有答案请如实告知。"
            "回复简洁不超过50字，但涉及赔偿政策、退款时效、金额条款时必须完整引用知识库内容。\n\n"
            f"参考知识：\n{knowledge}"
        )

        card_data = None
        action_keywords = ["帮我退", "申请退货", "我要退", "退款", "退货"]
        should_act = any(kw in user_msg for kw in action_keywords)

        if order_no and should_act:
            try:
                adapter = self.gateway.get_adapter()
                order = await adapter.get_order(order_no)
                if order and order.can_refund:
                    after_sale = await adapter.create_refund(order_no, user_msg[:50])
                    if after_sale:
                        card_data = {
                            "service_no": after_sale.service_no,
                            "status": after_sale.status,
                            "refund_amount": after_sale.refund_amount,
                            "order_no": order_no,
                            "progress": after_sale.progress,
                        }
                        system_content += (
                            f"\n\n【售后单已创建】单号：{after_sale.service_no}，"
                            f"状态：{after_sale.status}，"
                            f"退款金额：{after_sale.refund_amount/100:.2f}元。"
                            f"请在回复中告知用户售后单号和预计处理时间。"
                        )
                elif order:
                    system_content += (
                        f"\n\n该订单当前状态为「{order.status}」，不可退款。"
                        f"请在回复中告知用户当前订单状态，并说明不可退款的原因。"
                    )
                else:
                    system_content += "\n\n未找到该订单，请告知用户核实订单号。"
            except Exception as e:
                system_content += f"\n\n售后接口调用失败，请告知用户稍后重试。"

        system = {"role": "system", "content": system_content}
        msgs = [system] + history + [{"role": "user", "content": user_msg}]

        if card_data:
            yield json.dumps(
                {"type": "card", "card_type": "after_sale", "data": card_data},
                ensure_ascii=False,
            )

        async for token in self.llm.chat_stream(msgs):
            if token == "[DONE]":
                yield (
                    "__retrieval__:"
                    + json.dumps(
                        [{"text": r["text"], "score": r.get("score", 0)} for r in results],
                        ensure_ascii=False,
                    )
                )
                yield "[DONE]"
            else:
                yield token
