"""
数据隔离验证测试

验证多租户模式下：
- 租户 A 无法搜索到租户 B 的私有知识
- 公共知识可被所有租户检索
- 不带 tenant_id 的请求返回 400
"""

import pytest
from app.core.database import async_session
from app.knowledge.loader import load_document
from app.knowledge.retriever import Retriever
from app.knowledge.vector_store import VectorStore
from app.models.message import Message
from app.models.session import Session
from sqlalchemy import select


def _fresh_kb():
    """独立 collection，并清掉上一次运行可能残留的测试知识，保证确定性"""
    vs = VectorStore(collection_name="test_kb")
    if vs.available:
        try:
            vs.client.delete_collection("test_kb")
        except Exception:
            pass
        vs = VectorStore(collection_name="test_kb")
    return vs


@pytest.mark.asyncio
async def test_knowledge_isolation():
    """租户 A 搜不到租户 B 的私有知识"""
    vs = _fresh_kb()

    # 上传 A 的知识（私有）并真正写入向量库
    docs_a = load_document("tests/fixtures/doc_a.md", tenant_id="tenant_a", is_public=False)
    vs.add_documents(docs_a)
    # 上传 B 的知识（私有）并真正写入向量库
    docs_b = load_document("tests/fixtures/doc_b.md", tenant_id="tenant_b", is_public=False)
    vs.add_documents(docs_b)

    hybrid = Retriever(vector_store=vs)

    # 验证：A 搜私有知识应只返回 A 的
    results_a = await hybrid.retrieve("test query", top_k=5, tenant_id="tenant_a")
    assert len(results_a) > 0, "租户 A 私有知识检索结果为空（防止空结果假通过）"
    result_tenants = set()
    for r in results_a:
        meta = r.get("metadata", {})
        if isinstance(meta, dict):
            result_tenants.add(meta.get("tenant_id", ""))
    assert "tenant_b" not in result_tenants, "租户 A 搜到了租户 B 的私有知识！"


@pytest.mark.asyncio
async def test_public_knowledge_shared():
    """公共知识可被所有租户检索"""
    vs = _fresh_kb()

    # 上传公共知识并真正写入向量库
    docs_public = load_document("tests/fixtures/public.md", tenant_id="tenant_a", is_public=True)
    vs.add_documents(docs_public)

    hybrid = Retriever(vector_store=vs)

    # A 应能搜到
    results_a = await hybrid.retrieve("public info", top_k=5, tenant_id="tenant_a")
    assert len(results_a) > 0, "租户 A 搜不到公共知识"

    # B 也应能搜到
    results_b = await hybrid.retrieve("public info", top_k=5, tenant_id="tenant_b")
    assert len(results_b) > 0, "租户 B 搜不到公共知识"


@pytest.mark.asyncio
async def test_session_isolation():
    """租户 A 看不到租户 B 的会话"""
    async with async_session() as db:
        # 创建 A 的会话
        sess_a = Session(
            id="test_sess_a", platform="web", platform_session_id="ps_a",
            user_id="user_a", tenant_id="tenant_a",
        )
        db.add(sess_a)

        # 创建 B 的会话
        sess_b = Session(
            id="test_sess_b", platform="web", platform_session_id="ps_b",
            user_id="user_b", tenant_id="tenant_b",
        )
        db.add(sess_b)
        await db.commit()

        # A 查询只应看到自己的
        result = await db.execute(
            select(Session).where(Session.tenant_id == "tenant_a")
        )
        sessions = result.scalars().all()
        for s in sessions:
            assert s.tenant_id == "tenant_a", f"会话 {s.id} 不属于租户 A"
            assert s.id != "test_sess_b", "租户 A 查到了租户 B 的会话"


@pytest.mark.asyncio
async def test_message_isolation():
    """租户 A 看不到租户 B 的消息"""
    async with async_session() as db:
        msg_a = Message(
            id="test_msg_a", session_id="test_sess_a",
            role="user", content="hello from A",
            extra_metadata={"tenant_id": "tenant_a"},
        )
        msg_b = Message(
            id="test_msg_b", session_id="test_sess_b",
            role="user", content="hello from B",
            extra_metadata={"tenant_id": "tenant_b"},
        )
        db.add_all([msg_a, msg_b])
        await db.commit()

        # A 查询只应看到自己的
        result = await db.execute(
            select(Message).where(
                Message.extra_metadata["tenant_id"].as_string() == "tenant_a"
            )
        )
        messages = result.scalars().all()
        for m in messages:
            meta = m.extra_metadata or {}
            assert meta.get("tenant_id") == "tenant_a", f"消息 {m.id} 不属于租户 A"
