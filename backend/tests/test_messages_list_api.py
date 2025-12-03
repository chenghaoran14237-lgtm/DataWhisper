import os
from io import BytesIO

import pandas as pd
import pytest
import httpx

from app.core import database as db
from app.core.config import get_settings
from app.services.excel_service import excel_cache


@pytest.mark.asyncio
async def test_list_messages_returns_artifacts(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
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

    df = pd.DataFrame({"month": ["Jan", "Feb", "Mar"], "sales": [10, 20, 5]})
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

        # 触发一次趋势对话（应产生 chart artifacts）
        r = await client.post("/api/excel/chat", json={"session_id": sid, "upload_id": uid, "message": "sales 趋势"})
        assert r.status_code == 200

        # 拉消息列表
        m = await client.get(f"/api/sessions/{sid}/messages", params={"limit": 50})
        assert m.status_code == 200
        j = m.json()
        assert j["items"]
        roles = [x["role"] for x in j["items"]]
        assert "user" in roles and "assistant" in roles

        # assistant 消息应带 artifacts（至少一条有 chart）
        has_chart = any(
            (it["role"] == "assistant")
            and any(a.get("spec", {}).get("type") == "line" for a in it.get("artifacts", []))
            for it in j["items"]
        )
        assert has_chart

