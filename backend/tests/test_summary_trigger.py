import os
from io import BytesIO

import pandas as pd
import pytest
import httpx
from sqlalchemy import select

from app.core import database as db
from app.core.config import get_settings
from app.models.summary import Summary
from app.models.message import Message
from app.services.excel_service import excel_cache


@pytest.mark.asyncio
async def test_summary_is_created_and_messages_marked(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    # 让摘要几乎立刻触发（方便测试）
    os.environ["SUMMARY_TRIGGER_TOKENS"] = "1"
    os.environ["SUMMARY_MAX_CHARS"] = "800"

    get_settings.cache_clear()
    await db.shutdown_db()
    excel_cache.clear()

    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
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

        r = await client.post("/api/excel/chat", json={"session_id": sid, "upload_id": uid, "message": "测试摘要触发"})
        assert r.status_code == 200

    SessionLocal = db.get_sessionmaker()
    async with SessionLocal() as s:
        summ = (await s.execute(select(Summary).where(Summary.session_id == sid))).scalars().all()
        assert len(summ) == 1
        assert summ[0].up_to_message_id

        msgs = (await s.execute(select(Message).where(Message.session_id == sid))).scalars().all()
        assert len(msgs) >= 2
        assert all(m.summarized is True for m in msgs)  # 因为阈值=1，立刻全纳入 summary
