import os
from io import BytesIO

import pandas as pd
import pytest
import httpx
from sqlalchemy import select

from app.core import database as db
from app.core.config import get_settings
from app.models.message import Message
from app.services.excel_service import excel_cache


@pytest.mark.asyncio
async def test_tool_agent_trend_has_multisteps(tmp_path):
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

        r = await client.post("/api/excel/chat", json={"session_id": sid, "upload_id": uid, "message": "看一下 sales 的趋势"})
        assert r.status_code == 200

    # 去 DB 里抓 assistant message 的 debug，看工具链是否多步
    SessionLocal = db.get_sessionmaker()
    async with SessionLocal() as s:
        msgs = (await s.execute(
            select(Message).where(Message.session_id == sid, Message.role == "assistant")
        )).scalars().all()
        assert msgs

        debug = (msgs[-1].extra or {}).get("debug") or {}
        trace = debug.get("tool_trace") or []
        tools = [t["tool"] for t in trace]
        # 趋势计划：groupby_sum -> sort -> head
        assert "groupby_sum" in tools
        assert "sort_time" in tools
        assert "head" in tools
