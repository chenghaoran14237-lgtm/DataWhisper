from __future__ import annotations

import pandas as pd


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]


def analyze_question(df: pd.DataFrame, question: str) -> str:
    q = question.strip().lower()
    num_cols = _numeric_cols(df)

    if df.empty:
        return "表格为空（0 行），无法计算。"

    # 总和
    if any(k in q for k in ["总和", "合计", "sum"]):
        if not num_cols:
            return "表格中没有数值列（numeric columns），无法做总和。"
        s = df[num_cols].sum(numeric_only=True).to_dict()
        lines = ["数值列总和："]
        for k, v in s.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    # 平均
    if any(k in q for k in ["平均", "均值", "mean", "avg"]):
        if not num_cols:
            return "表格中没有数值列，无法做均值。"
        m = df[num_cols].mean(numeric_only=True).to_dict()
        lines = ["数值列均值："]
        for k, v in m.items():
            lines.append(f"- {k}: {v}")
        return "\n".join(lines)

    # 最大/最小
    if any(k in q for k in ["最大", "max"]):
        if not num_cols:
            return "表格中没有数值列，无法做最大值。"
        mx = df[num_cols].max(numeric_only=True).to_dict()
        return "数值列最大值：\n" + "\n".join([f"- {k}: {v}" for k, v in mx.items()])

    if any(k in q for k in ["最小", "min"]):
        if not num_cols:
            return "表格中没有数值列，无法做最小值。"
        mn = df[num_cols].min(numeric_only=True).to_dict()
        return "数值列最小值：\n" + "\n".join([f"- {k}: {v}" for k, v in mn.items()])

    # 趋势（非常简化版：如果有日期列或 month 列，按它 groupby）
    if any(k in q for k in ["趋势", "走势", "trend"]):
        # 尝试找一个“像时间”的列
        time_candidates = [c for c in df.columns if str(c).lower() in ["date", "datetime", "month", "月份", "日期"]]
        if time_candidates and num_cols:
            tcol = time_candidates[0]
            g = df.groupby(tcol)[num_cols].sum(numeric_only=True).reset_index()
            return "按时间列汇总（sum）：\n" + g.head(20).to_string(index=False)
        # 找不到就退化为 describe
        desc = df.describe(include="all").fillna("").to_string()
        return "未找到明显时间列，先给你全表描述统计（describe）：\n" + desc[:1200]

    # 默认：快速画像 + describe 摘要
    head = df.head(5).fillna("").astype(str).to_string(index=False)
    desc = df.describe(include="all").fillna("").to_string()
    return "前 5 行预览：\n" + head + "\n\n描述统计（节选）：\n" + desc[:1200]
