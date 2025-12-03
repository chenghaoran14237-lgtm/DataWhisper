from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FileUpload(Base):
    __tablename__ = "file_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # upload_id
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("sessions.id"), nullable=False)

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_path: Mapped[str] = mapped_column(String(1024), nullable=False)

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        nullable=False,
    )
