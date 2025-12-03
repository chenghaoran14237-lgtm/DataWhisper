from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    settings = get_settings()
    return {"status": "ok", "app": settings.app_name, "env": settings.env}
