from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.file_upload import FileUpload
from app.models.session import Session

from sqlalchemy import select
from app.models.file_upload import FileUpload

# upload_id -> {"df": DataFrame, "profile": dict}
excel_cache: dict[str, dict[str, Any]] = {}


class ExcelService:
    @staticmethod
    def _uploads_dir() -> Path:
        settings = get_settings()
        base = Path(settings.data_dir)
        (base / "uploads").mkdir(parents=True, exist_ok=True)
        return base / "uploads"

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        # 防止前端传 “C:\xxx\abc.xlsx” 这种路径形式
        return Path(name).name

    @staticmethod
    async def save_and_cache_excel(
        db: AsyncSession,
        session_id: str,
        file: UploadFile,
    ) -> tuple[FileUpload, dict[str, Any]]:
        settings = get_settings()

        if not file.filename:
            raise HTTPException(status_code=400, detail="missing filename")

        filename = ExcelService._sanitize_filename(file.filename)
        if not filename.lower().endswith(".xlsx"):
            raise HTTPException(status_code=400, detail="only .xlsx is supported")

        # session 必须存在
        sess = await db.get(Session, session_id)
        if sess is None:
            raise HTTPException(status_code=404, detail="session not found")

        upload_id = str(uuid.uuid4())
        stored_path = ExcelService._uploads_dir() / f"{upload_id}.xlsx"

        # 流式写文件 + 大小限制
        max_bytes = int(settings.max_upload_mb) * 1024 * 1024
        size = 0
        try:
            with stored_path.open("wb") as f:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > max_bytes:
                        raise HTTPException(
                            status_code=413,
                            detail=f"file too large (>{settings.max_upload_mb}MB)",
                        )
                    f.write(chunk)
        finally:
            await file.close()

        # 读 Excel -> DataFrame（默认第一个 sheet），失败就清理文件
        try:
            df = pd.read_excel(stored_path)  # 默认 sheet0
        except Exception as e:
            stored_path.unlink(missing_ok=True)
            raise HTTPException(status_code=400, detail=f"invalid xlsx: {type(e).__name__}")

        # 生成基础 profile（给后续 LLM 用的“预览结构”）
        profile = {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "columns": [str(c) for c in df.columns.tolist()],
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "missing_rate": {str(k): float(v) for k, v in df.isna().mean().items()},
            "preview": (
                df.head(10)
                .fillna("")
                .astype(str)
                .to_dict(orient="records")
            ),
        }

        # 入库：file_uploads + 更新 session.current_upload_id
        rec = FileUpload(
            id=upload_id,
            session_id=session_id,
            filename=filename,
            stored_path=str(stored_path),
        )
        db.add(rec)
        sess.current_upload_id = upload_id
        await db.commit()
        await db.refresh(rec)

        # 缓存 DataFrame（不入库）
        excel_cache[upload_id] = {"df": df, "profile": profile}

        return rec, profile

    @staticmethod
    def get_profile(upload_id: str) -> Optional[dict[str, Any]]:
        item = excel_cache.get(upload_id)
        if not item:
            return None
        return item.get("profile")

    @staticmethod
    def get_df(upload_id: str):
        item = excel_cache.get(upload_id)
        if not item:
            return None
        return item.get("df")

    @staticmethod
    async def ensure_cached(db: AsyncSession, upload_id: str) -> dict[str, Any] | None:
        """保证 excel_cache 里有该 upload_id 的 df/profile；没有就从 stored_path 回填。"""
        item = excel_cache.get(upload_id)
        if item and item.get("df") is not None and item.get("profile") is not None:
            return item

        fu = (await db.execute(select(FileUpload).where(FileUpload.id == upload_id))).scalar_one_or_none()
        if fu is None:
            return None

        stored_path = Path(fu.stored_path)
        if not stored_path.exists():
            return None

        df = pd.read_excel(stored_path)

        profile = {
            "rows": int(df.shape[0]),
            "cols": int(df.shape[1]),
            "columns": [str(c) for c in df.columns.tolist()],
            "dtypes": {str(k): str(v) for k, v in df.dtypes.items()},
            "missing_rate": {str(k): float(v) for k, v in df.isna().mean().items()},
            "preview": df.head(10).fillna("").astype(str).to_dict(orient="records"),
        }

        excel_cache[upload_id] = {"df": df, "profile": profile}
        return excel_cache[upload_id]