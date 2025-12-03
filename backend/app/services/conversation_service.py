from __future__ import annotations

import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message

from app.core.config import get_settings
from app.services.summary_service import SummaryService
from app.models.message import Message

from sqlalchemy import select, or_, and_
from app.models.message import Message

class ConversationService:
    @staticmethod
    def estimate_token_count(text: str) -> int:
        # 超粗略估算：中文/英文混合时也“差不多能用”
        # 后面接真正 tokenizer（tiktoken）再升级
        return max(1, len(text) // 4)

    @staticmethod
    async def add_message(
        db: AsyncSession,
        session_id: str,
        role: str,
        content: str,
        extra: Optional[dict[str, Any]] = None,
        token_count: Optional[int] = None,
    ) -> Message:
        mid = str(uuid.uuid4())
        msg = Message(
            id=mid,
            session_id=session_id,
            role=role,
            content=content,
            extra=extra,
            token_count=token_count if token_count is not None else ConversationService.estimate_token_count(content),
        )
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return msg

    @staticmethod
    async def list_recent(
        db: AsyncSession,
        session_id: str,
        limit: int = 50,
    ) -> list[Message]:
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())
    
    @staticmethod
    async def list_unsummarized_recent(db, session_id: str, limit: int | None = None) -> list[Message]:
        if limit is None:
            limit = get_settings().context_recent_limit

        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.summarized == False)  # noqa: E712
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        msgs = list(res.scalars().all())
        msgs.reverse()  # chronological
        return msgs

    @staticmethod
    async def build_llm_context(db, session_id: str) -> list[dict]:
        """
        规则：最新 summary（若有） + 最近未总结消息（N条）；
        并控制总 token 不超过预算（超了就裁剪更老的消息）。
        """
        settings = get_settings()

        ctx: list[dict] = []
        latest = await SummaryService.get_latest(db, session_id)
        if latest:
            ctx.append({"role": "system", "content": f"Conversation summary:\n{latest.content}"})

        msgs = await ConversationService.list_unsummarized_recent(db, session_id, settings.context_recent_limit)
        for m in msgs:
            ctx.append({"role": m.role, "content": m.content})

        # token 预算裁剪：优先删掉“更老的”非 summary 消s息
        def est(item: dict) -> int:
            return ConversationService.estimate_token_count(item["content"] or "")

        total = sum(est(x) for x in ctx)
        if total <= settings.max_context_tokens:
            return ctx

        # ctx[0] 可能是 summary，尽量保留；从最早的历史开始删
        start_idx = 1 if (ctx and ctx[0]["role"] == "system") else 0
        i = start_idx
        while total > settings.max_context_tokens and i < len(ctx) - 1:
            total -= est(ctx[i])
            ctx.pop(i)

        # 如果 summary 太大仍超：截断 summary
        if ctx and ctx[0]["role"] == "system" and total > settings.max_context_tokens:
            keep = max(300, settings.summary_max_chars // 2)
            ctx[0]["content"] = ctx[0]["content"][-keep:]
        return ctx
    
    
    @staticmethod
    async def list_messages_page(
        db,
        session_id: str,
        limit: int = 50,
        cursor: str | None = None,   # cursor=上一页最后一条 message.id
    ) -> tuple[list[Message], str | None, bool]:
        limit = max(1, min(int(limit), 200))

        base = (
            select(Message)
            .where(Message.session_id == session_id)
        )

        # 如果有 cursor，用 (created_at, id) 做稳定分页
        if cursor:
            cur = await db.get(Message, cursor)
            if cur is not None and cur.session_id == session_id:
                base = base.where(
                    or_(
                        Message.created_at < cur.created_at,
                        and_(Message.created_at == cur.created_at, Message.id < cur.id),
                    )
                )

        stmt = base.order_by(Message.created_at.desc(), Message.id.desc()).limit(limit + 1)
        res = await db.execute(stmt)
        rows = list(res.scalars().all())

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        next_cursor = rows[-1].id if (has_more and rows) else None

        # 前端一般要正序显示
        rows.reverse()
        return rows, next_cursor, has_more
