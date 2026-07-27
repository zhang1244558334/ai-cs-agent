import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class BargainLog(Base):
    __tablename__ = "bargain_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("sessions.id"), index=True
    )
    round: Mapped[int] = mapped_column(default=1)
    user_offer: Mapped[float] = mapped_column()
    agent_offer: Mapped[float] = mapped_column()
    discount_given: Mapped[float] = mapped_column(default=0.0)
    temperature: Mapped[float] = mapped_column(default=0.3)
    result: Mapped[str] = mapped_column(String(16), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
