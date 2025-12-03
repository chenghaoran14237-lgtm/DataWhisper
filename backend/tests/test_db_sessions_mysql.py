import os
import uuid

import pytest
from sqlalchemy import select

from app.core.config import get_settings
from app.core import database as db
from app.models.session import Session


@pytest.mark.asyncio
async def test_mysql_session_insert_and_query():
    # 指向测试库（强烈建议只在测试库上 drop/create）
    os.environ["DATABASE_URL"] = (
        "mysql+aiomysql://datawhisper:dwpass@127.0.0.1:3306/datawhisper_test?charset=utf8mb4"
    )

    # 清 Settings 缓存 + 重置 engine
    get_settings.cache_clear()
    await db.shutdown_db()

    # 重建表（只对 test 库）
    engine = db.get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(db.Base.metadata.drop_all)
        await conn.run_sync(db.Base.metadata.create_all)

    SessionLocal = db.get_sessionmaker()
    sid = str(uuid.uuid4())

    async with SessionLocal() as s:
        s.add(Session(id=sid, status="active", meta={"hello": "mysql"}))
        await s.commit()

    async with SessionLocal() as s:
        res = await s.execute(select(Session).where(Session.id == sid))
        got = res.scalar_one()
        assert got.status == "active"
        assert got.meta["hello"] == "mysql"
