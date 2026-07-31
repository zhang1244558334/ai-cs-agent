import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), default='single')
    platform: Mapped[str] = mapped_column(String(32), index=True)
    platform_session_id: Mapped[str] = mapped_column(String(128), unique=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True)
    item_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(16), default="ai")
    last_intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    bargain_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", MutableDict.as_mutable(JSON), nullable=True
    )

    __table_args__ = (
        Index("idx_sessions_platform_user", "platform", "user_id", "updated_at"),
        Index("idx_sessions_platform_sid", "platform", "platform_session_id", unique=True),
    )
