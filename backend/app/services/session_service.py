import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.session import Session


class SessionService:
    @staticmethod
    async def create(db: AsyncSession, meta: Optional[dict[str, Any]] = None) -> Session:
        sid = str(uuid.uuid4())
        obj = Session(id=sid, status="active", meta=meta)
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return obj

    @staticmethod
    async def get(db: AsyncSession, session_id: str) -> Optional[Session]:
        res = await db.execute(select(Session).where(Session.id == session_id))
        return res.scalar_one_or_none()
