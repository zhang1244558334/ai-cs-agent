import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, async_session, engine
from app.main import app


@pytest.fixture(autouse=True)
async def setup_db():
    # Import all models so their metadata is registered on Base.metadata
    from app.models import Session, Message, Item, BargainLog, HandoverLog  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(setup_db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_returns_200(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_chat_returns_501(client: AsyncClient):
    resp = await client.post("/api/chats")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_create_and_query_session():
    from app.models import Session

    async with async_session() as session:
        sess = Session(
            platform="web",
            platform_session_id="test_sid_004",
            user_id="test_user",
        )
        session.add(sess)
        await session.commit()

        result = await session.get(Session, sess.id)
        assert result is not None
        assert result.user_id == "test_user"
        assert result.mode == "ai"
