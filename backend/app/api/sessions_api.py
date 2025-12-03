from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.session_schemas import SessionCreateRequest, SessionResponse
from app.services.session_service import SessionService

from app.schemas.message_schemas import MessagesPage, MessageItem
from app.services.conversation_service import ConversationService


router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreateRequest, db: AsyncSession = Depends(get_db)):
    return await SessionService.create(db, meta=payload.meta)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str, db: AsyncSession = Depends(get_db)):
    obj = await SessionService.get(db, session_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="session not found")
    return obj

@router.get("/{session_id}/messages", response_model=MessagesPage)
async def list_messages(
    session_id: str,
    limit: int = 50,
    cursor: str | None = None,
    include_debug: bool = False,
    db: AsyncSession = Depends(get_db),
):
    # session 不存在就 404（避免无意义查库）
    obj = await SessionService.get(db, session_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="session not found")

    msgs, next_cursor, has_more = await ConversationService.list_messages_page(
        db, session_id=session_id, limit=limit, cursor=cursor
    )

    items: list[MessageItem] = []
    for m in msgs:
        extra = m.extra or {}
        debug = extra.get("debug") or {}
        artifacts = debug.get("artifacts", []) if isinstance(debug, dict) else []
        items.append(
            MessageItem(
                id=m.id,
                role=m.role,
                content=m.content,
                created_at=m.created_at,
                artifacts=artifacts if isinstance(artifacts, list) else [],
                extra=extra if include_debug else None,
            )
        )

    return MessagesPage(items=items, next_cursor=next_cursor, has_more=has_more)
