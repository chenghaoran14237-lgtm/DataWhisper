import os
from io import BytesIO

import pandas as pd
import pytest
import httpx

from app.core.config import get_settings
from app.core import database as db
from app.services.excel_service import excel_cache


@pytest.mark.asyncio
async def test_trend_without_time_uses_index_chart(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["LLM_PROVIDER"] = "fake"
    os.environ["DATABASE_URL"] = "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"

    get_settings.cache_clear()
    await db.shutdown_db()
    excel_cache.clear()

    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    df = pd.DataFrame({"学生姓名": ["张三", "李四", "王五"], "任务点完成百分比": [95, 88, 76]})
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

        r = await client.post("/api/excel/chat", json={"session_id": sid, "upload_id": uid, "message": "任务点完成百分比 趋势图"})
        assert r.status_code == 200
        artifacts = r.json().get("artifacts") or []
        assert artifacts
        spec = artifacts[0]["spec"]
        assert spec["type"] == "line"
        assert spec["x"]["name"] == "index"  # ✅ 兜底走 index
