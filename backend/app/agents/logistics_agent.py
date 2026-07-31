import re

from app.core.config import settings
from app.knowledge.retriever import Retriever
from app.platforms.factory import PlatformGateway
from app.platforms.mock_adapter import _PHONE_TAIL

from .base_agent import BaseAgent

_PHONE_TAIL_RE = re.compile(r"(\d{4})")


class LogisticsAgent(BaseAgent):
    def __init__(self, llm_client=None):
        super().__init__(llm_client)
        self.retriever = Retriever(alpha=0.7)
        self.gateway = PlatformGateway()

    async def chat_stream(self, messages: list, order_no: str | None = None):
        history = messages[:-1]
        user_msg = messages[-1]["content"] if messages else ""
        results = await self.retriever.retrieve(user_msg)
        knowledge = (
            "\n\n".join([r["text"] for r in results]) if results else "未找到相关信息"
        )
        system_content = (
            "你是物流客服助手。参考以下知识回答用户关于发货、快递、物流时效、配送、签收的问题，"
            "如果知识库没有答案请如实告知。回复简洁不超过50字。\n\n"
            f"参考知识：\n{knowledge}"
        )
        if order_no is None:
            system_content += "\n\n用户未提供订单号，请先向用户询问订单号，不要编造物流信息"
        elif settings.platform.verify:
            tail = self._extract_phone_tail(user_msg)
            expected = _PHONE_TAIL.get(order_no)
            if tail is None:
                system_content += "\n\n请向用户询问手机尾号以验证订单归属"
            elif expected is None or tail != expected:
                system_content += "\n\n订单验证失败，请告知用户核实订单号或手机尾号"
            else:
                tracking_text = await self._fetch_tracking(order_no)
                if tracking_text:
                    system_content += f"\n\n实时物流信息：\n{tracking_text}"
        else:
            tracking_text = await self._fetch_tracking(order_no)
            if tracking_text:
                system_content += f"\n\n实时物流信息：\n{tracking_text}"
        system = {"role": "system", "content": system_content}
        msgs = [system] + history + [{"role": "user", "content": user_msg}]
        async for token in self.llm.chat_stream(msgs):
            yield token

    @staticmethod
    def _extract_phone_tail(user_msg: str) -> str | None:
        matches = _PHONE_TAIL_RE.findall(user_msg)
        return matches[-1] if matches else None

    async def _fetch_tracking(self, order_no: str | None) -> str:
        if order_no is None:
            return ""
        try:
            adapter = self.gateway.get_adapter()
            info = await adapter.get_tracking(order_no)
        except Exception:
            return ""
        if info is None:
            return "未查询到该订单的物流信息"
        recent = info.trace[-1] if info.trace else None
        recent_text = (
            f"{recent.time} {recent.node}（{recent.city}）"
            if recent and recent.node
            else ""
        )
        parts = [
            f"承运商：{info.carrier}",
            f"运单号：{info.tracking_no}",
            f"当前状态：{info.status}",
        ]
        if recent_text:
            parts.append(f"最近节点：{recent_text}")
        if info.eta:
            parts.append(f"预计送达：{info.eta}")
        return "；".join(parts)
