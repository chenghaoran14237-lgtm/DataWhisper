from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)
    up_to_message_id: Mapped[str] = mapped_column(String(36), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
