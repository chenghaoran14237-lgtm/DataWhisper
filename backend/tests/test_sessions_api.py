import os

import pytest
import httpx

from app.core.config import get_settings
from app.core import database as db


@pytest.mark.asyncio
async def test_create_and_get_session_api():
    os.environ["ENV"] = "test"
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    get_settings.cache_clear()
    await db.shutdown_db()

    # 重建表（干净环境）
    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    from app.main import create_app  # env 设置后再 import
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post("/api/sessions", json={"meta": {"from": "test"}})
        assert r.status_code == 201
        data = r.json()
        sid = data["id"]
        assert data["status"] == "active"
        assert data["meta"]["from"] == "test"

        r2 = await client.get(f"/api/sessions/{sid}")
        assert r2.status_code == 200
        data2 = r2.json()
        assert data2["id"] == sid
