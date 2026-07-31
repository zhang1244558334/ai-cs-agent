import json
import os

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.attribution.engine import AttributionEngine
from app.core.database import async_session
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

router = APIRouter()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
PATCHES_DIR = os.path.join(PROJECT_ROOT, "data/auto_patches")


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
    count = await engine.analyze_batch()
    return {"status": "ok", "processed": count}


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
