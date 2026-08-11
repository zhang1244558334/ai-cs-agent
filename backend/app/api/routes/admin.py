import json
import os

import yaml
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.attribution.engine import AttributionEngine
from app.core.config import settings
from app.core.database import async_session
from app.models.message import Message
from app.models.tenant import Tenant
from pydantic import BaseModel


class TenantCreate(BaseModel):
    name: str
    contact_email: str
    api_key: str
    knowledge_sharing_enabled: bool = False


class TenantUpdate(BaseModel):
    name: str | None = None
    contact_email: str | None = None
    api_key: str | None = None
    knowledge_sharing_enabled: bool | None = None


class SettingsUpdate(BaseModel):
    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    max_discount: float | None = None
    max_rounds: int | None = None
    platform_config: str | None = None
    platform_provider: str | None = None

router = APIRouter()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
PATCHES_DIR = os.path.join(PROJECT_ROOT, "data/auto_patches")
SETTINGS_FILE = os.path.join(PROJECT_ROOT, "config", "settings.json")


def _load_status(dirpath: str) -> str:
    path = os.path.join(dirpath, "status.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f).get("status", "pending")
    return "pending"


def _scan_proposals() -> dict:
    l1, l2, l3 = [], [], []
    if not os.path.isdir(PATCHES_DIR):
        return {"l1": l1, "l2": l2, "l3": l3}
    for entry in sorted(os.listdir(PATCHES_DIR), reverse=True):
        proposal_path = os.path.join(PATCHES_DIR, entry, "proposal.json")
        if not os.path.isfile(proposal_path):
            continue
        with open(proposal_path, encoding="utf-8") as f:
            proposal = json.load(f)
        item = {
            "id": entry,
            "action": proposal.get("action", ""),
            "target": proposal.get("target", ""),
            "content": proposal.get("content", ""),
            "level": proposal.get("level", "L3"),
            "attribution_type": proposal.get("attribution_type", "D"),
            "detail": proposal.get("detail", ""),
            "status": _load_status(os.path.join(PATCHES_DIR, entry)),
        }
        level = item["level"]
        if level == "L1":
            l1.append(item)
        elif level == "L2":
            l2.append(item)
        else:
            l3.append(item)
    return {"l1": l1, "l2": l2, "l3": l3}


@router.get("/api/admin/dashboard")
async def dashboard(tenant_id: str = "ecommerce"):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    async with async_session() as db:
        result = await db.execute(
            select(Message).where(
                Message.created_at >= today_start,
                Message.tenant_id == tenant_id,
            )
        )
        today_msgs = result.scalars().all()
        today = len(today_msgs)
        flagged = sum(1 for m in today_msgs if (m.extra_metadata or {}).get("quality_flag") == "factual_error")

        result = await db.execute(
            select(Message)
            .where(Message.role == "assistant", Message.tenant_id == tenant_id)
            .order_by(Message.created_at.desc())
            .limit(5)
        )
        recent_msgs = result.scalars().all()
        recent_chats = [
            {
                "id": m.id,
                "content": m.content[:100],
                "intent": (m.extra_metadata or {}).get("intent", ""),
                "created_at": str(m.created_at),
            }
            for m in recent_msgs
        ]

    proposals_data = _scan_proposals()
    proposals = (
        len(proposals_data["l1"]) + len(proposals_data["l2"]) + len(proposals_data["l3"])
    )
    all_proposals = sorted(
        proposals_data["l1"] + proposals_data["l2"] + proposals_data["l3"],
        key=lambda x: x["id"],
        reverse=True,
    )[:5]
    recent_proposals = all_proposals

    # 意图分布统计（最近24小时）
    from sqlalchemy import func
    async with async_session() as db:
        result = await db.execute(
            select(Message).where(
                Message.created_at >= today_start,
                Message.tenant_id == tenant_id,
            )
        )
        all_today = result.scalars().all()
    intent_counts = {}
    for m in all_today:
        intent = (m.extra_metadata or {}).get("intent", "default")
        intent_counts[intent] = intent_counts.get(intent, 0) + 1
    intent_stats = [{"name": k, "value": v} for k, v in intent_counts.items()]

    # 24小时会话量趋势（按小时）
    from datetime import timedelta
    hourly = {}
    for i in range(24):
        slot_start = today_start - timedelta(hours=23-i)
        slot_end = slot_start + timedelta(hours=1)
        hourly[slot_start.strftime("%H:00")] = 0
    async with async_session() as db:
        result = await db.execute(
            select(Message).where(
                Message.created_at >= today_start - timedelta(hours=23),
                Message.tenant_id == tenant_id,
            )
        )
        all_24h = result.scalars().all()
    for m in all_24h:
        hour_key = m.created_at.strftime("%H:00") if hasattr(m.created_at, 'strftime') else m.created_at[:13] + ":00"
        if hour_key in hourly:
            hourly[hour_key] += 1
    hourly_stats = [{"hour": k, "count": v} for k, v in hourly.items()]

    return {
        "health": "ok",
        "today": today,
        "flagged": flagged,
        "proposals": proposals,
        "intent_stats": intent_stats,
        "hourly_stats": hourly_stats,
        "recent_chats": recent_chats,
        "recent_proposals": recent_proposals,
    }


@router.get("/api/admin/proposals")
async def list_proposals():
    return _scan_proposals()


def _write_status(proposal_id: str, status: str) -> dict:
    dirpath = os.path.join(PATCHES_DIR, proposal_id)
    if not os.path.isdir(dirpath):
        raise HTTPException(status_code=404, detail="proposal not found")
    path = os.path.join(dirpath, "status.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"status": status}, f, ensure_ascii=False, indent=2)
    return {"id": proposal_id, "status": status}


@router.post("/api/admin/proposals/{proposal_id}/approve")
async def approve_proposal(proposal_id: str):
    return _write_status(proposal_id, "approved")


@router.post("/api/admin/proposals/{proposal_id}/reject")
async def reject_proposal(proposal_id: str):
    return _write_status(proposal_id, "rejected")


@router.post("/api/admin/proposals/{proposal_id}/defer")
async def defer_proposal(proposal_id: str):
    return _write_status(proposal_id, "deferred")


@router.post("/api/admin/proposals/{proposal_id}/done")
async def done_proposal(proposal_id: str):
    return _write_status(proposal_id, "done")


@router.post("/api/admin/attribution/run")
async def run_attribution():
    engine = AttributionEngine()
    flagged = await engine.analyze_flagged_messages()
    handover = await engine.analyze_batch()
    return {"flagged": flagged, "handover": handover}


@router.post("/api/admin/seed-events")
async def seed_events():
    import subprocess, os
    result = subprocess.run(
        ["python3", "scripts/seed_proactive.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    return {"status": "ok", "output": result.stdout.strip().split(chr(10))}


@router.post("/api/admin/auto-execute")
async def auto_execute():
    import subprocess, os
    result = subprocess.run(
        ["python3", "scripts/auto_execute.py"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    return {"status": "ok", "output": result.stdout.strip().split(chr(10))}


@router.post("/api/admin/weekly-report")
async def weekly_report():
    import subprocess, os
    result = subprocess.run(
        ["python3", "scripts/attribution_report.py", "--report", "weekly"],
        capture_output=True, text=True, cwd=PROJECT_ROOT
    )
    return {"status": "ok", "output": result.stdout.strip().split(chr(10))}


@router.post("/api/admin/settings")
async def save_settings(body: SettingsUpdate):
    existing = {}
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            existing = json.load(f)
    merged = {**existing, **body.model_dump(exclude_none=True)}
    os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
    with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    # 同步所有字段到运行时，实现热切换无需重启
    if body.platform_config is not None:
        settings.platform_config = body.platform_config
    if body.platform_provider is not None:
        settings.platform.provider = body.platform_provider
    if body.model is not None:
        settings.llm_model = body.model
    if body.base_url is not None:
        settings.llm_base_url = body.base_url
    if body.api_key is not None:
        settings.llm_api_key = body.api_key
    return {"status": "ok"}


@router.get("/api/admin/settings")
async def get_settings():
    """返回当前保存的设置（脱敏处理api_key）"""
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}
    # api_key 脱敏：只显示前后各4位
    key = data.get("api_key", "")
    if key and len(key) > 8:
        data["api_key_masked"] = key[:4] + "****" + key[-4:]
    elif key:
        data["api_key_masked"] = "****"
    # 不返回完整api_key给前端（安全），前端用自己的缓存
    data.pop("api_key", None)
    return data


@router.post("/api/admin/tenants")
async def create_tenant(body: TenantCreate):
    tenant = Tenant(
        name=body.name,
        contact_email=body.contact_email,
        api_key=body.api_key,
        knowledge_sharing_enabled=body.knowledge_sharing_enabled,
    )
    async with async_session() as db:
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name}


@router.get("/api/admin/tenants")
async def list_tenants():
    async with async_session() as db:
        result = await db.execute(
            select(Tenant).where(Tenant.is_active == True)
        )
        tenants = result.scalars().all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "contact_email": t.contact_email,
            "knowledge_sharing_enabled": t.knowledge_sharing_enabled,
            "is_active": t.is_active,
            "created_at": str(t.created_at),
        }
        for t in tenants
    ]


@router.patch("/api/admin/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, body: TenantUpdate):
    async with async_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant not found")
        if body.name is not None:
            tenant.name = body.name
        if body.contact_email is not None:
            tenant.contact_email = body.contact_email
        if body.api_key is not None:
            tenant.api_key = body.api_key
        if body.knowledge_sharing_enabled is not None:
            tenant.knowledge_sharing_enabled = body.knowledge_sharing_enabled
        await db.commit()
        await db.refresh(tenant)
    return {"id": tenant.id, "name": tenant.name}


@router.delete("/api/admin/tenants/{tenant_id}")
async def deactivate_tenant(tenant_id: str):
    async with async_session() as db:
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="tenant not found")
        tenant.is_active = False
        await db.commit()
    return {"id": tenant_id, "status": "deactivated"}


@router.get("/api/admin/platforms")
async def list_platforms():
    """返回可用平台列表及其凭证字段定义"""
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))),
        "config", "platforms.yaml"
    )
    if not os.path.exists(config_path):
        return {"platforms": [{"key": "mock", "name": "模拟数据", "icon": "flask-conical", "fields": [], "description": "使用内置模拟数据"}]}
    with open(config_path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    platforms = []
    for key, cfg in raw.items():
        platforms.append({
            "key": key,
            "name": cfg.get("name", key),
            "icon": cfg.get("icon", "server"),
            "fields": cfg.get("fields", []),
            "description": cfg.get("description", ""),
        })
    return {"platforms": platforms}


@router.post("/api/admin/platforms/activate")
async def activate_platform(body: dict):
    """切换平台提供商"""
    provider = body.get("provider", "mock")
    from app.platforms.factory import PlatformGateway

    try:
        PlatformGateway.switch_provider(provider)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"provider": provider, "status": "activated"}
