from __future__ import annotations

from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.conversation_service import ConversationService
from app.services.excel_service import ExcelService
from app.services.llm_service import get_llm_provider
from app.services.planner import plan_tools, ToolCall
from app.services.tools.default_registry import build_default_registry


class AgentService:
    @staticmethod
    def _format_tool_results(trace: list[dict[str, Any]]) -> str:
        lines: list[str] = []
        for i, t in enumerate(trace, start=1):
            lines.append(f"[Step {i}] {t['tool']} args={t['args']}")
            lines.append(t["output_preview"])
            lines.append("")
        return "\n".join(lines).strip()

    @staticmethod
    async def answer_excel_question(
        db: AsyncSession,
        *,
        session_id: str,
        upload_id: str,
        question: str,
    ) -> tuple[str, dict]:
        cached = await ExcelService.ensure_cached(db, upload_id)
        if not cached:
            return "我找不到对应的上传文件（可能被删除或路径无效）。", {"error": "upload_missing"}

        df = cached["df"]
        profile = cached["profile"]

        plan: list[ToolCall] = plan_tools(df, question)

        reg = build_default_registry()
        trace: list[dict[str, Any]] = []
        artifacts: list[dict[str, Any]] = []   # ✅ 关键：先定义
        current_df = df

        for call in plan:
            fn = reg.get(call.name)
            out = fn(current_df, **call.args)

            trace.append(
                {
                    "tool": call.name,
                    "args": call.args,
                    "output_kind": out.kind,
                    "output_preview": out.preview,
                }
            )

            if out.kind == "table":
                current_df = out.value

            if out.kind == "chart":
                # ✅ 缩进修正
                artifacts.append({"kind": "chart", "spec": out.value})

        tool_result = AgentService._format_tool_results(trace)

        ctx = await ConversationService.build_llm_context(db, session_id)
        ctx_text = "\n".join([f"{m['role']}: {m['content']}" for m in ctx][-20:])

        system = (
            "你是一个数据分析助手。必须基于工具输出回答，不要编造。\n"
            f"数据概况：rows={profile['rows']}, cols={profile['cols']}, columns={profile['columns']}\n"
            f"最近对话（节选）：\n{ctx_text}"
        )

        llm = get_llm_provider()
        reply = await llm.generate(system=system, user=question, tool_result=tool_result)

        debug = {
            "plan": [{"tool": p.name, "args": p.args} for p in plan],
            "tool_trace": trace,
            "artifacts": artifacts,  # ✅ 现在一定存在
            "profile": {"rows": profile["rows"], "cols": profile["cols"], "columns": profile["columns"][:20]},
        }
        return reply, debug
