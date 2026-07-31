import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), default='single')
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    content_type: Mapped[str] = mapped_column(String(16), default="text")
    extra_metadata: Mapped[dict | None] = mapped_column(
        "metadata", MutableDict.as_mutable(JSON), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_messages_session_created", "session_id", "created_at"),
    )
