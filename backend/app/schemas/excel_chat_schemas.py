from typing import Any
from pydantic import BaseModel, Field


class ExcelChatRequest(BaseModel):
    session_id: str
    upload_id: str
    message: str


class ExcelChatResponse(BaseModel):
    reply: str
    session_id: str
    upload_id: str
    artifacts: list[dict[str, Any]] = Field(default_factory=list)
