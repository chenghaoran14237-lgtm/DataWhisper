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
async def test_excel_chat_writes_messages(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["MAX_UPLOAD_MB"] = "10"
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    get_settings.cache_clear()
    await db.shutdown_db()
    excel_cache.clear()

    # 重建表（包含 messages/file_uploads/sessions）
    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    # 造一个 xlsx
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
            files={
                "file": (
                    "demo.xlsx",
                    bio.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert up.status_code == 200
        upj = up.json()
        sid, uid = upj["session_id"], upj["upload_id"]

        chat = await client.post(
            "/api/excel/chat",
            json={"session_id": sid, "upload_id": uid, "message": "请帮我分析销售趋势"},
        )
        assert chat.status_code == 200
        cj = chat.json()
        assert cj["session_id"] == sid
        assert cj["upload_id"] == uid
        assert "计算结果" in cj["reply"]


    # 验证 DB 里写了两条消息
    SessionLocal = db.get_sessionmaker()
    async with SessionLocal() as s:
        msgs = (await s.execute(select(Message).where(Message.session_id == sid))).scalars().all()
        roles = [m.role for m in msgs]
        assert "user" in roles
        assert "assistant" in roles
