from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # UUID 字符串
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),  # MySQL 对 timezone 的支持很有限，建议统一存 UTC/本地约定
        server_default=func.now(),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_upload_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)

    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
