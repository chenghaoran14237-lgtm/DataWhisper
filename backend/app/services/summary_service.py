from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.message import Message
from app.models.summary import Summary


class SummaryService:
    @staticmethod
    async def get_latest(db: AsyncSession, session_id: str) -> Summary | None:
        stmt = (
            select(Summary)
            .where(Summary.session_id == session_id)
            .order_by(Summary.created_at.desc(), Summary.id.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    @staticmethod
    async def list_unsummarized(db: AsyncSession, session_id: str) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.summarized == False)  # noqa: E712
            .order_by(Message.created_at.asc(), Message.id.asc())
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def should_summarize(db: AsyncSession, session_id: str) -> bool:
        settings = get_settings()
        msgs = await SummaryService.list_unsummarized(db, session_id)
        total = sum((m.token_count or 0) for m in msgs)
        return total >= settings.summary_trigger_tokens

    @staticmethod
    def build_summary_text(prev: str | None, msgs: list[Message]) -> str:
        settings = get_settings()
        base = (prev or "").strip()

        lines: list[str] = []
        if not base:
            lines.append("【会话摘要】")
        else:
            lines.append(base)
            lines.append("\n【增量摘要】")

        for m in msgs:
            one_line = " ".join((m.content or "").split())
            one_line = one_line[:120]
            lines.append(f"- {m.role}: {one_line}")

        text = "\n".join(lines)

        # 控制摘要体积（demo 先用字符长度，后续可换 token）
        if len(text) > settings.summary_max_chars:
            text = text[-settings.summary_max_chars :]

        return text

    @staticmethod
    async def create_or_update(db: AsyncSession, session_id: str) -> Summary | None:
        msgs = await SummaryService.list_unsummarized(db, session_id)
        if not msgs:
            return None

        latest = await SummaryService.get_latest(db, session_id)
        new_content = SummaryService.build_summary_text(latest.content if latest else None, msgs)

        up_to_message_id = msgs[-1].id
        s = Summary(
            id=str(uuid.uuid4()),
            session_id=session_id,
            content=new_content,
            up_to_message_id=up_to_message_id,
        )
        db.add(s)

        # 标记这批消息已纳入总结（符合 described：summarized 字段用途）:contentReference[oaicite:6]{index=6}
        for m in msgs:
            m.summarized = True

        await db.commit()
        await db.refresh(s)
        return s

    @staticmethod
    async def maybe_summarize(db: AsyncSession, session_id: str) -> Summary | None:
        if await SummaryService.should_summarize(db, session_id):
            return await SummaryService.create_or_update(db, session_id)
        return None
