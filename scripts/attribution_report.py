import argparse
import json
import os
import sys
from collections import Counter
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select

from app.core.config import settings
from app.core.database import async_session
from app.models.handover_log import HandoverLog

ATTRIBUTION_LABELS = {"A": "知识库缺失", "B": "路由错误", "C": "话术问题", "D": "正常转接"}
REPORTS_DIR = "reports"
PATCHES_DIR = "data/auto_patches"
BAR_WIDTH = 30


def _bar(ratio: float) -> str:
    filled = round(ratio * BAR_WIDTH)
    return "█" * filled + "░" * (BAR_WIDTH - filled)


async def _fetch_attributions(week_offset: int) -> list[HandoverLog]:
    since = datetime.utcnow() - timedelta(weeks=week_offset)
    async with async_session() as db:
        result = await db.execute(
            select(HandoverLog).where(
                HandoverLog.attribution_type.isnot(None),
                HandoverLog.attribution_type != "",
                HandoverLog.created_at >= since,
            )
        )
        return list(result.scalars().all())


def _patch_stats() -> dict:
    stats = {"total": 0, "executed": 0, "rolled_back": 0, "pending": 0, "other": 0}
    if not os.path.isdir(PATCHES_DIR):
        return stats
    for entry in os.listdir(PATCHES_DIR):
        status_path = os.path.join(PATCHES_DIR, entry, "status.json")
        if os.path.isfile(status_path):
            with open(status_path, encoding="utf-8") as f:
                status = json.load(f).get("status", "pending")
        else:
            status = "pending"
        stats["total"] += 1
        if status in stats:
            stats[status] += 1
        else:
            stats["other"] += 1
    return stats


def _top_issues(logs: list[HandoverLog]) -> list[tuple[str, int]]:
    details = []
    for log in logs:
        if log.attribution_detail:
            try:
                d = json.loads(log.attribution_detail)
                if isinstance(d, dict) and d.get("detail"):
                    details.append(d["detail"][:60])
            except (json.JSONDecodeError, AttributeError):
                pass
    return Counter(details).most_common(3)


def _suggestions(logs: list[HandoverLog]) -> list[tuple[str, int]]:
    suggs = []
    for log in logs:
        if log.attribution_detail:
            try:
                d = json.loads(log.attribution_detail)
                if isinstance(d, dict) and d.get("suggestion"):
                    suggs.append(d["suggestion"][:80])
            except (json.JSONDecodeError, AttributeError):
                pass
    return Counter(suggs).most_common(5)


def _render(logs: list[HandoverLog], week_offset: int) -> str:
    total = len(logs)
    counter = Counter(log.attribution_type for log in logs)
    patches = _patch_stats()

    since = (datetime.utcnow() - timedelta(weeks=week_offset)).strftime("%Y-%m-%d")
    lines = []
    lines.append(f"# 客服归因周报 ({since} ~ 至今)")
    lines.append("")
    lines.append(f"## 概览")
    lines.append(f"- 归因总数：**{total}**")
    lines.append(f"- 已执行改进：**{patches['executed']}**")
    lines.append(f"- 回滚次数：**{patches['rolled_back']}**")
    lines.append("")

    lines.append("## 归因分布")
    lines.append("")
    lines.append(f"| 类型 | 数量 | 占比 | 分布 |")
    lines.append(f"|------|-----:|-----:|------|")
    for code in ("A", "B", "C", "D"):
        lbl = ATTRIBUTION_LABELS.get(code, code)
        cnt = counter.get(code, 0)
        pct = cnt / total * 100 if total else 0
        bar = _bar(pct / 100)
        lines.append(f"| {code} {lbl} | {cnt} | {pct:.1f}% | {bar} |")
    lines.append("")

    lines.append("## Top-3 高频问题")
    lines.append("")
    for i, (issue, cnt) in enumerate(_top_issues(logs), 1):
        lines.append(f"{i}. 「{issue}」 (出现 {cnt} 次)")
    lines.append("")

    lines.append("## 改进建议汇总")
    lines.append("")
    for i, (sug, cnt) in enumerate(_suggestions(logs), 1):
        lines.append(f"{i}. {sug} (提及 {cnt} 次)")
    lines.append("")

    lines.append("## 改进执行统计")
    lines.append("")
    lines.append(f"| 指标 | 数值 |")
    lines.append(f"|------|-----:|")
    lines.append(f"| 总提案 | {patches['total']} |")
    lines.append(f"| 已执行 | {patches['executed']} |")
    lines.append(f"| 已回滚 | {patches['rolled_back']} |")
    lines.append(f"| 待处理 | {patches['pending']} |")
    if patches["total"]:
        rate = patches["executed"] / patches["total"] * 100
        lines.append(f"| 执行成功率 | {rate:.1f}% |")
    lines.append("")

    return "\n".join(lines)


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="weekly", choices=["weekly"])
    parser.add_argument("--week", type=int, default=1, help="weeks to look back")
    args = parser.parse_args()

    logs = await _fetch_attributions(args.week)
    md = _render(logs, args.week)

    os.makedirs(REPORTS_DIR, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(REPORTS_DIR, f"weekly_{ts}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"report saved to {path}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
