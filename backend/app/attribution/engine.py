import json
import os
from datetime import datetime

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.core.llm import LLMClient
from app.models.handover_log import HandoverLog

ATTRIBUTION_TYPES = {
    "A": "知识库缺失",
    "B": "路由错误",
    "C": "话术问题",
    "D": "正常转接",
}

SYSTEM_PROMPT = (
    "分析客服对话失败原因。"
    "A:知识库缺失 B:路由错误 C:话术问题 D:正常转接。"
    "只返回 JSON。"
)


class AttributionEngine:
    def __init__(self):
        self.llm = LLMClient(
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            temperature=0.2,
            max_tokens=512,
        )

    async def analyze(
        self,
        message: str,
        intent: str,
        context_history: list,
        knowledge_results: list,
    ) -> dict:
        context_str = json.dumps(context_history[-5:], ensure_ascii=False)
        knowledge_str = json.dumps(knowledge_results[:3], ensure_ascii=False)
        user_prompt = (
            f"消息:{message}\n意图:{intent}\n"
            f"上下文:{context_str}\n知识库:{knowledge_str}\n"
            f'输出 JSON: {{"type":"A/B/C/D","confidence":0.0~1.0,"detail":"","suggestion":""}}'
        )
        raw = await self.llm.chat([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ])
        return self._parse(raw)

    def _parse(self, raw: str) -> dict:
        try:
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```")
            data = json.loads(raw)
            return {
                "type": data.get("type", "D"),
                "confidence": float(data.get("confidence", 0)),
                "detail": data.get("detail", ""),
                "suggestion": data.get("suggestion", ""),
            }
        except Exception:
            return {"type": "D", "confidence": 0, "detail": raw[:200], "suggestion": ""}

    @staticmethod
    def _level(confidence: float) -> str:
        if confidence >= 0.95:
            return "L1"
        if confidence >= 0.7:
            return "L2"
        return "L3"

    def generate_proposal(
        self, attribution_type: str, detail: str, suggestion: str, confidence: float
    ) -> dict:
        level = self._level(confidence)
        targets = {
            "A": {"action": "add_faq", "target": "docs/"},
            "B": {"action": "update_rules", "target": "config/router_rules.yaml"},
            "C": {"action": "optimize_prompt", "target": "prompts/"},
        }
        base = targets.get(attribution_type, {})
        return {
            "attribution_type": attribution_type,
            "action": base.get("action", ""),
            "target": base.get("target", ""),
            "content": suggestion,
            "detail": detail,
            "level": level,
        }

    def save_proposal(self, proposal: dict) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"data/auto_patches/{ts}"
        os.makedirs(path, exist_ok=True)
        filepath = os.path.join(path, "proposal.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(proposal, f, ensure_ascii=False, indent=2)
        return filepath

    async def analyze_batch(self):
        async with async_session() as db:
            result = await db.execute(
                select(HandoverLog).where(
                    (HandoverLog.attribution_type == "") | (HandoverLog.attribution_type.is_(None))
                )
            )
            logs = result.scalars().all()

        count = 0
        for log in logs:
            result = await self.analyze(
                message=log.reason,
                intent=log.to_mode,
                context_history=[],
                knowledge_results=[],
            )
            log.attribution_type = result["type"]
            log.attribution_detail = json.dumps(
                {"detail": result["detail"], "suggestion": result["suggestion"]},
                ensure_ascii=False,
            )
            async with async_session() as db:
                await db.merge(log)
                await db.commit()
            count += 1
        return count
