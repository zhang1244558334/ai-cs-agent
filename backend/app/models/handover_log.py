import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class HandoverLog(Base):
    __tablename__ = "handover_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    tenant_id: Mapped[str] = mapped_column(String(36), default='single')
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), index=True
    )
    switched_by: Mapped[str] = mapped_column(String(32))
    from_mode: Mapped[str] = mapped_column(String(16))
    to_mode: Mapped[str] = mapped_column(String(16))
    reason: Mapped[str] = mapped_column(Text, default="")
    routing_result: Mapped[str] = mapped_column(Text, nullable=True, default="")
    human_response: Mapped[str] = mapped_column(Text, nullable=True, default="")
    attribution_type: Mapped[str] = mapped_column(String(16), nullable=True, default="")
    attribution_detail: Mapped[str] = mapped_column(Text, nullable=True, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
