import argparse
import csv
import json
import os
import sys
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import func as sa_func, select

from app.core.config import settings
from app.core.database import async_session
from app.models.handover_log import HandoverLog
from app.models.message import Message
from app.models.session import Session

REPORTS_DIR = "reports/tracking"
PATCHES_DIR = "data/auto_patches"


def _month_range(year: int, month: int) -> tuple[str, str]:
    start = f"{year:04d}-{month:02d}-01 00:00:00"
    if month == 12:
        end = f"{year + 1:04d}-01-01 00:00:00"
    else:
        end = f"{year:04d}-{month + 1:02d}-01 00:00:00"
    return start, end


async def _count_handovers(year: int, month: int) -> int:
    start, end = _month_range(year, month)
    async with async_session() as db:
        result = await db.execute(
            select(sa_func.count(HandoverLog.id)).where(
                HandoverLog.created_at >= start,
                HandoverLog.created_at < end,
            )
        )
        return result.scalar() or 0


async def _count_sessions(year: int, month: int) -> int:
    start, end = _month_range(year, month)
    async with async_session() as db:
        result = await db.execute(
            select(sa_func.count(Session.id)).where(
                Session.created_at >= start,
                Session.created_at < end,
            )
        )
        return result.scalar() or 0


async def _message_stats(year: int, month: int) -> tuple[int, int]:
    start, end = _month_range(year, month)
    async with async_session() as db:
        msg_result = await db.execute(
            select(sa_func.count(Message.id)).where(
                Message.created_at >= start,
                Message.created_at < end,
            )
        )
        total_msgs = msg_result.scalar() or 0
        sess_result = await db.execute(
            select(sa_func.count(sa_func.distinct(Message.session_id))).where(
                Message.created_at >= start,
                Message.created_at < end,
            )
        )
        total_sessions = sess_result.scalar() or 0
    return total_msgs, total_sessions


def _patch_stats(year: int, month: int) -> dict:
    prefix = f"{year:04d}{month:02d}"
    total = 0
    statuses = Counter()
    if not os.path.isdir(PATCHES_DIR):
        return {"total": 0, "executed": 0, "rolled_back": 0, "verified": 0, "failed": 0}
    for entry in os.listdir(PATCHES_DIR):
        if not entry.startswith(prefix):
            continue
        total += 1
        sp = os.path.join(PATCHES_DIR, entry, "status.json")
        if os.path.isfile(sp):
            with open(sp, encoding="utf-8") as f:
                statuses[json.load(f).get("status", "pending")] += 1
        else:
            statuses["pending"] += 1
    return {
        "total": total,
        "executed": statuses.get("executed", 0) + statuses.get("verified", 0),
        "rolled_back": statuses.get("rolled_back", 0),
        "verified": statuses.get("verified", 0),
        "failed": statuses.get("verification_failed", 0),
    }


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=datetime.now().year)
    parser.add_argument("--month", type=int, default=datetime.now().month)
    args = parser.parse_args()

    handover_count = await _count_handovers(args.year, args.month)
    session_count = await _count_sessions(args.year, args.month)
    msg_count, msg_sessions = await _message_stats(args.year, args.month)
    patches = _patch_stats(args.year, args.month)

    handover_rate = handover_count / session_count if session_count else 0
    avg_turns = msg_count / msg_sessions if msg_sessions else 0
    exec_rate = patches["executed"] / patches["total"] if patches["total"] else 0

    os.makedirs(REPORTS_DIR, exist_ok=True)
    path = os.path.join(REPORTS_DIR, f"{args.year:04d}_{args.month:02d}.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["year", args.year])
        w.writerow(["month", args.month])
        w.writerow(["handover_count", handover_count])
        w.writerow(["session_count", session_count])
        w.writerow(["handover_rate", f"{handover_rate:.4f}"])
        w.writerow(["total_messages", msg_count])
        w.writerow(["message_sessions", msg_sessions])
        w.writerow(["avg_turns_per_session", f"{avg_turns:.2f}"])
        w.writerow(["patches_total", patches["total"]])
        w.writerow(["patches_executed", patches["executed"]])
        w.writerow(["patches_rolled_back", patches["rolled_back"]])
        w.writerow(["patches_verified", patches["verified"]])
        w.writerow(["patches_failed", patches["failed"]])
        w.writerow(["execution_rate", f"{exec_rate:.4f}"])

    print(f"tracking report saved to {path}")
    print(f"  handover_rate={handover_rate:.2%}, avg_turns={avg_turns:.2f}, exec_rate={exec_rate:.2%}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
