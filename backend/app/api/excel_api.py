from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.excel_schemas import ExcelUploadResponse
from app.services.excel_service import ExcelService
from app.services.session_service import SessionService

from fastapi import HTTPException
from sqlalchemy import select

from app.models.file_upload import FileUpload
from app.services.conversation_service import ConversationService
from app.schemas.excel_chat_schemas import ExcelChatRequest, ExcelChatResponse
from app.services.excel_service import excel_cache  # 用于测试/调试可见（可不导出也行）

from app.services.summary_service import SummaryService

from app.services.agent_service import AgentService

router = APIRouter(prefix="/excel", tags=["excel"])


@router.post("/upload", response_model=ExcelUploadResponse)
async def upload_excel(
    file: UploadFile = File(...),
    session_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    # 允许前端不提前创建 session：没传就自动建
    if not session_id:
        sess = await SessionService.create(db, meta={"created_by": "excel_upload"})
        session_id = sess.id

    rec, profile = await ExcelService.save_and_cache_excel(db, session_id=session_id, file=file)
    return ExcelUploadResponse(
        session_id=session_id,
        upload_id=rec.id,
        filename=rec.filename,
        profile=profile,
    )

@router.post("/chat", response_model=ExcelChatResponse)
async def excel_chat(payload: ExcelChatRequest, db: AsyncSession = Depends(get_db)):
    # 1) 文本长度保护（需求里建议做输入长度限制，避免“玩死自己”）:contentReference[oaicite:5]{index=5}
    if len(payload.message) > 2000:
        raise HTTPException(status_code=400, detail="message too long (>2000 chars)")

    # 2) upload 必须属于该 session
    fu = (
        await db.execute(
            select(FileUpload).where(
                FileUpload.id == payload.upload_id,
                FileUpload.session_id == payload.session_id,
            )
        )
    ).scalar_one_or_none()
    if fu is None:
        raise HTTPException(status_code=404, detail="upload not found for this session")

    # 3) 取 Excel profile（优先缓存；缓存丢了就简单报错，下一模块我们做“磁盘回填缓存”）
    prof = ConversationService  # 占位避免 linter 抱怨
    profile = None
    cached = __import__("app.services.excel_service", fromlist=["excel_cache"]).excel_cache
    item = cached.get(payload.upload_id)
    if item:
        profile = item.get("profile")
    if not profile:
        raise HTTPException(status_code=409, detail="excel cache miss (please re-upload for now)")

    # 4) 写入 user message
    await ConversationService.add_message(
        db,
        session_id=payload.session_id,
        role="user",
        content=payload.message,
        extra={"upload_id": payload.upload_id},
    )

    # 5) 生成一个“假回复”（先把链路跑通；下一模块接 Agent/LLM）
    cols_preview = ", ".join(profile["columns"][:8])
    reply, debug = await AgentService.answer_excel_question(
    db,
    session_id=payload.session_id,
    upload_id=payload.upload_id,
    question=payload.message,
)
    artifacts = (debug or {}).get("artifacts", [])  # ✅ 永远有值：list
# 写入 assistant message（extra 里存 debug 简版）
    await ConversationService.add_message(
        db,
        session_id=payload.session_id,
        role="assistant",
        content=reply,
        extra={"upload_id": payload.upload_id, "mode": "agent", "debug": debug},
    )

    await SummaryService.maybe_summarize(db, payload.session_id)

    #return ExcelChatResponse(reply=reply, session_id=payload.session_id, upload_id=payload.upload_id)
    return ExcelChatResponse(
        reply=reply,
        session_id=payload.session_id,
        upload_id=payload.upload_id,
        artifacts=artifacts,
    )
   
