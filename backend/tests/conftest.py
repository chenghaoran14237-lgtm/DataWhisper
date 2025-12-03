import pytest_asyncio

from app.core import database as db
from app.core.config import get_settings


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_async_resources():
    yield
    await db.shutdown_db()
    get_settings.cache_clear()
