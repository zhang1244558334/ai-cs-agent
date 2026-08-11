import os
import json

from fastapi import APIRouter, HTTPException

router = APIRouter()

BUSINESS_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data", "businesses.json")
DOCS_BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "docs"))


def _load_businesses() -> list[dict]:
    if not os.path.exists(BUSINESS_FILE):
        default = [{"id": "ecommerce", "name": "电商客服", "icon": "shopping-cart", "active": True,
                      "prompt": _default_prompt("电商客服")}]
        os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
        with open(BUSINESS_FILE, "w", encoding="utf-8") as f:
            json.dump(default, f, ensure_ascii=False, indent=2)
        return default
    with open(BUSINESS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_businesses(data: list[dict]):
    os.makedirs(os.path.dirname(BUSINESS_FILE), exist_ok=True)
    with open(BUSINESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _default_prompt(name: str) -> str:
    return (
        f"你是{name}助手，负责回答用户关于{name}相关的问题。\n"
        "【身份规则】禁止透露你是AI或机器人；自称'我'，称呼用户为'您'。\n"
        "【回复规则】①回复简洁，日常对话不超过50字。②参考知识库内容回答，知识库没有的直接说'抱歉，我暂时无法回答'，禁止编造。③用户说'我说了XX'是在纠正你，立刻承认并调整。"
    )


@router.get("/api/businesses")
async def list_businesses():
    return {"businesses": _load_businesses()}


@router.post("/api/businesses")
async def create_business(body: dict):
    businesses = _load_businesses()
    bid = body["name"].lower().replace(" ", "_")
    if any(b["id"] == bid for b in businesses):
        raise HTTPException(400, f"Business '{bid}' already exists")
    businesses.append({
        "id": bid,
        "name": body["name"],
        "icon": body.get("icon", "building-2"),
        "active": True,
        "prompt": body.get("prompt") or _default_prompt(body["name"]),
    })
    os.makedirs(os.path.join(DOCS_BASE, bid), exist_ok=True)
    _save_businesses(businesses)
    return {"businesses": businesses}


@router.put("/api/businesses/{business_id}")
async def update_business(business_id: str, body: dict):
    businesses = _load_businesses()
    for b in businesses:
        if b["id"] == business_id:
            if "name" in body:
                b["name"] = body["name"]
            if "icon" in body:
                b["icon"] = body["icon"]
            if "active" in body:
                b["active"] = body["active"]
            _save_businesses(businesses)
            return {"businesses": businesses}
    raise HTTPException(404, f"Business '{business_id}' not found")


@router.delete("/api/businesses/{business_id}")
async def delete_business(business_id: str):
    if business_id == "ecommerce":
        raise HTTPException(400, "Cannot delete default ecommerce business")
    businesses = _load_businesses()
    businesses = [b for b in businesses if b["id"] != business_id]
    _save_businesses(businesses)
    return {"businesses": businesses}
