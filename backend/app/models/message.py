from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)

    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user/assistant/system
    content: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )

    summarized: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("0"),
        default=False,
    )

    token_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    extra: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
