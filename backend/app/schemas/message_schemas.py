from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
    extra: Optional[dict[str, Any]] = None  # include_debug=true 时才会带


class MessagesPage(BaseModel):
    items: list[MessageItem]
    next_cursor: Optional[str] = None
    has_more: bool = False
