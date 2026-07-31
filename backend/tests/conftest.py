"""backend/tests 共享配置：把数据库隔离到独立测试库，避免污染真实 data/chat.db。"""
import os

os.environ["CS_DATABASE_URL"] = "sqlite+aiosqlite:///./data/test_tenant.db"

import pytest
from app.core import database as database_mod
from app.core.config import settings
from app.models import Message, Session, Tenant  # noqa: F401  注册表结构
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

settings.database_url = os.environ["CS_DATABASE_URL"]

database_mod.engine = create_async_engine(settings.database_url, echo=settings.debug)
database_mod.async_session = async_sessionmaker(
    database_mod.engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(autouse=True)
async def init_db():
    """建表 + 每次测试前清空 sessions/messages（测试库清表安全，不影响真实 data/chat.db）"""
    from app.core.database import Base

    async with database_mod.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with database_mod.async_session() as db:
        await db.execute(delete(Message))
        await db.execute(delete(Session))
        await db.commit()
    yield
