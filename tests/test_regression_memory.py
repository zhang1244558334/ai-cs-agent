"""端到端回归测试：多轮上下文 / tech 路由 / 删除同步向量。

所有 LLM 调用均用 mock 固定返回值，不调用真实 API、不依赖外网。
运行方式（standalone）：
    pytest tests/test_regression_memory.py -v
"""
import os

os.environ["CS_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_regression.db"

import uuid  # noqa: E402

import pytest  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.core.llm import LLMClient  # noqa: E402
from app.main import app  # noqa: E402
from app.router.intent_vector_matcher import IntentVectorMatcher  # noqa: E402
from app.router.llm_classifier import LLMClassifier  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

TEST_DB = "./data/test_regression.db"


@pytest.fixture(autouse=True)
async def setup_db():
    from app.models import (  # noqa: F401
        BargainLog,
        HandoverLog,
        Item,
        Message,
        ProactiveLog,
        Session,
        Tenant,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


@pytest.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def _spy_stream(captured: list):
    def _chat_stream(self, messages):
        captured.append(messages)

        async def _gen():
            yield "好的"
            yield "[DONE]"

        return _gen()

    return _chat_stream


async def _fake_chat(self, messages):
    return "综合前文为您解答"


async def _fake_classify(self, text):
    return "default"


def _patch_no_llm(monkeypatch, captured: list):
    monkeypatch.setattr(LLMClient, "chat_stream", _spy_stream(captured))
    monkeypatch.setattr(LLMClient, "chat", _fake_chat)
    monkeypatch.setattr(LLMClassifier, "classify", _fake_classify)
    monkeypatch.setattr(IntentVectorMatcher, "query", lambda self, t: None)


@pytest.mark.asyncio
async def test_scene_a_multi_turn_context(client, monkeypatch):
    """场景A：多轮上下文。最后一次 LLM 调用必须携带历史消息（len > 2）。"""
    captured: list = []
    _patch_no_llm(monkeypatch, captured)

    sid = f"mem_{uuid.uuid4()}"
    turns = ["我我看了一个商品", "一款润肤霜", "我是油性皮肤", "你有什么推荐吗"]
    for msg in turns:
        resp = await client.post(
            "/api/chats",
            params={
                "platform": "web",
                "platform_session_id": sid,
                "user_id": "reg_user",
                "message": msg,
            },
        )
        assert resp.status_code == 200
        await resp.aread()

    assert len(captured) == len(turns), f"chat_stream 应被调用 {len(turns)} 次"
    last_msgs = captured[-1]
    assert len(last_msgs) > 2, f"历史上下文未传入: len(messages)={len(last_msgs)}"
    contents = [m["content"] for m in last_msgs]
    assert any("我我看了一个商品" in c for c in contents), "早期上下文缺失"
    print(f"PASS: 最后一次 LLM 调用收到 {len(last_msgs)} 条消息（含历史上下文）")


@pytest.mark.asyncio
async def test_scene_b_tech_uses_tech_agent(client, monkeypatch):
    """场景B：tech 意图走 TechAgent（带 RAG），而非 default_agent。"""
    captured: list = []

    class FakeTechAgent:
        instances = []

        def __init__(self, llm_client=None):
            FakeTechAgent.instances.append(self)
            self.llm = type("L", (), {"chat_stream": _spy_stream(captured)})()

        async def chat_stream(self, messages):
            async for token in self.llm.chat_stream(messages):
                yield token

    import app.agents.tech_agent as tech_mod

    monkeypatch.setattr(tech_mod, "TechAgent", FakeTechAgent)
    _patch_no_llm(monkeypatch, captured)

    resp = await client.post(
        "/api/chats",
        params={
            "platform": "web",
            "platform_session_id": f"tech_{uuid.uuid4()}",
            "user_id": "reg_user",
            "message": "键盘参数是多少",
        },
    )
    assert resp.status_code == 200
    await resp.aread()

    assert FakeTechAgent.instances, "tech 意图未走 TechAgent"
    assert captured, "TechAgent 未走流式输出"
    print("PASS: tech 意图正确走 TechAgent（带 RAG），SSE 流式输出正常")


@pytest.mark.asyncio
async def test_scene_c_delete_syncs_vector(client):
    """场景C：删除文档时同步删除 Chroma 向量，无残留。"""
    from app.knowledge.vector_store import VectorStore

    vs = VectorStore()
    if not vs.available:
        pytest.skip("Chroma 不可用，跳过")

    docs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "docs"))
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    fn = "verify_regression.md"
    filepath = os.path.join(docs_dir, fn)
    seed_source = os.path.join(project_root, "scripts", "..", "docs", fn)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("**Q: 回归测试文档？**\nA: 这是用于验证删除同步的临时文档。")

    from app.knowledge.loader import load_document

    chunks = load_document(seed_source)
    vs.add_documents(chunks)
    stored = vs.collection.get(where={"source": seed_source})
    assert stored.get("ids"), "seed 失败：Chroma 未存入向量"
    print(f"  seeded {len(stored['ids'])} chunk(s)")

    resp = await client.delete(f"/api/knowledge/{fn}")
    assert resp.status_code == 200
    assert not os.path.exists(filepath), "磁盘文件未被删除"

    remaining = vs.collection.get(where={"source": seed_source})
    assert not remaining.get("ids"), f"Chroma 残留: {remaining.get('ids')}"

    hits = vs.search("回归测试")
    assert not any("回归测试" in r["text"] for r in hits), "删除后仍可检索到该文档"
    print("PASS: 删除文档后 Chroma 无残留且不可检索")
