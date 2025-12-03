import os
from io import BytesIO

import pandas as pd
import pytest
import httpx
from sqlalchemy import select

from app.core import database as db
from app.core.config import get_settings
from app.models.file_upload import FileUpload
from app.models.session import Session


@pytest.mark.asyncio
async def test_excel_upload_creates_session_and_upload(tmp_path):
    os.environ["ENV"] = "test"
    os.environ["DATA_DIR"] = str(tmp_path)
    os.environ["MAX_UPLOAD_MB"] = "10"
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    get_settings.cache_clear()
    await db.shutdown_db()

    # 重建表
    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    # 构造一个 xlsx 到内存
    df = pd.DataFrame({"month": ["Jan", "Feb"], "sales": [10, 20]})
    bio = BytesIO()
    df.to_excel(bio, index=False, engine="openpyxl")
    bio.seek(0)

    from app.main import create_app
    app = create_app()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/excel/upload",
            files={
                "file": (
                    "demo.xlsx",
                    bio.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )
        assert r.status_code == 200
        data = r.json()
        assert "session_id" in data
        assert "upload_id" in data
        assert data["filename"] == "demo.xlsx"
        assert data["profile"]["rows"] == 2
        assert "preview" in data["profile"]

        sid = data["session_id"]
        uid = data["upload_id"]

    # 校验：文件落盘
    saved = tmp_path / "uploads" / f"{uid}.xlsx"
    assert saved.exists()

    # 校验：DB 写入 file_uploads + 更新 sessions.current_upload_id
    SessionLocal = db.get_sessionmaker()
    async with SessionLocal() as s:
        fu = (await s.execute(select(FileUpload).where(FileUpload.id == uid))).scalar_one()
        assert fu.session_id == sid

        sess = (await s.execute(select(Session).where(Session.id == sid))).scalar_one()
        assert sess.current_upload_id == uid
