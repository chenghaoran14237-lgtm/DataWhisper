from typing import Any, Dict, List

from pydantic import BaseModel


class ExcelUploadResponse(BaseModel):
    session_id: str
    upload_id: str
    filename: str
    profile: Dict[str, Any]
