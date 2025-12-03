from fastapi import APIRouter
from .health_api import router as health_router
from .sessions_api import router as sessions_router
from .excel_api import router as excel_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(sessions_router)
api_router.include_router(excel_router)
