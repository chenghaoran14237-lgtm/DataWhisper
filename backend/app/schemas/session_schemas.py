from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict


class SessionCreateRequest(BaseModel):
    meta: Optional[dict[str, Any]] = None


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
    status: str
    current_upload_id: Optional[str] = None
    meta: Optional[dict[str, Any]] = None
