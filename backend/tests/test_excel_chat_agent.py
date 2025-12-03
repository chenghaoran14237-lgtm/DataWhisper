import os
from io import BytesIO

import pandas as pd
import pytest
import httpx

from app.core import database as db
from app.core.config import get_settings
from app.services.excel_service import excel_cache


@pytest.mark.asyncio
async def test_excel_chat_agent_sum(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["MAX_UPLOAD_MB"] = "10"
    os.environ["LLM_PROVIDER"] = "fake"
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    get_settings.cache_clear()
    await db.shutdown_db()
    excel_cache.clear()

    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    df = pd.DataFrame({"month": ["Jan", "Feb"], "sales": [10, 20]})
    bio = BytesIO()
    df.to_excel(bio, index=False, engine="openpyxl")
    bio.seek(0)

    from app.main import create_app
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        up = await client.post(
            "/api/excel/upload",
            files={"file": ("demo.xlsx", bio.read(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        sid = up.json()["session_id"]
        uid = up.json()["upload_id"]

        r = await client.post(
            "/api/excel/chat",
            json={"session_id": sid, "upload_id": uid, "message": "请给我 sales 的总和"},
        )
        assert r.status_code == 200
        reply = r.json()["reply"]
        assert "sales" in reply.lower() or "sales" in reply
        assert "30" in reply  # 10 + 20
