from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import re
from difflib import SequenceMatcher


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]


def _lower(s: str) -> str:
    return (s or "").lower()


def _normalize_text(s: str) -> str:
    s = (s or "").strip().lower()

    # 常见同义表达归一化（按你项目的表格语境来）
    synonyms = {
        "完成率": "完成百分比",
        "完成度": "完成百分比",
        "%": "百分比",
        "％": "百分比",
        "占比": "百分比",
        "进度条": "进度",
    }
    for a, b in synonyms.items():
        s = s.replace(a, b)

    # 去掉一些噪声符号/括号/标点/多空格
    s = re.sub(r"[\s\(\)\[\]（）【】{}<>《》,，.。:：;；!！?？'\"“”‘’\-_/\\]+", "", s)
    return s


def _ngrams(s: str, nmin: int = 2, nmax: int = 4) -> set[str]:
    s = _normalize_text(s)
    out: set[str] = set()
    if not s:
        return out
    for n in range(nmin, nmax + 1):
        if len(s) < n:
            continue
        for i in range(0, len(s) - n + 1):
            out.add(s[i : i + n])
    return out


def _score_column(question: str, col: str) -> float:
    qn = _normalize_text(question)
    cn = _normalize_text(col)

    if not cn:
        return 0.0

    # 1) 直接包含：权重最高
    if cn in qn:
        return 1000.0 + len(cn)

    # 2) 2~4 字 n-gram 重合
    qg = _ngrams(qn)
    cg = _ngrams(cn)
    inter = len(qg & cg)
    union = max(1, len(qg | cg))
    jaccard = inter / union  # 0~1

    # 3) 序列相似度兜底
    seq = SequenceMatcher(None, qn, cn).ratio()  # 0~1

    return inter * 5.0 + jaccard * 50.0 + seq * 30.0


def _match_cols(question: str, columns: list[str], top_k: int = 3) -> list[str]:
    scored = [(c, _score_column(question, c)) for c in columns]
    scored.sort(key=lambda x: x[1], reverse=True)

    picked = [c for c, s in scored if s >= 8.0][:top_k]
    return picked


def _pick_time_col(columns: list[str]) -> str | None:
    candidates = {"date", "datetime", "time", "month", "year", "日期", "时间", "月份", "月", "年"}
    for c in columns:
        if _lower(c) in candidates:
            return c
    return None


def _numeric_cols(df: pd.DataFrame) -> list[str]:
    """
    识别“可用于数值计算”的列：
    - 原生 numeric dtype 直接算
    - object/string：尝试 to_numeric（支持百分号、逗号），只要至少有 1 个可转数值且占比不太离谱就算
      （这样 2 行里 1 个缺失也仍然算数值列）
    """
    out: list[str] = []
    n = len(df)

    for c in df.columns:
        # 1) 原生数值列
        if pd.api.types.is_numeric_dtype(df[c]):
            out.append(str(c))
            continue

        # 2) 字符串列：清洗后尝试转数值
        s0 = df[c]

        # 处理 "95%"、"1,234"、空格等常见情况
        s_clean = (
            s0.astype(str)
            .str.replace(r"[%％]", "", regex=True)
            .str.replace(",", "", regex=False)
            .str.strip()
        )

        s = pd.to_numeric(s_clean, errors="coerce")
        non_na = int(s.notna().sum())
        if non_na == 0:
            continue

        ratio = non_na / max(1, n)

        # ✅ 阈值放宽：允许小样本缺失（2 行有 1 个缺失 => 0.5 通过）
        # 经验：>= 0.2 就够用；同时要求至少 1 个可转数值
        if ratio >= 0.2:
            out.append(str(c))

    return out



def _mentioned_cols(df: pd.DataFrame, q: str) -> list[str]:
    cols = [str(c) for c in df.columns]
    ql = q.lower()
    hit = []
    for c in cols:
        if c.lower() in ql:
            hit.append(c)
    return hit


def plan_tools(df: pd.DataFrame, question: str) -> list[ToolCall]:
    cols = [str(c) for c in df.columns.tolist()]
    q = _lower(question)

    matched = _match_cols(question, cols)
    num_cols = _numeric_cols(df)
    matched_numeric = [c for c in matched if c in num_cols]

    # ---------------------------------------------------------
    # ✅ 规则 0：总和 / 合计 / sum / total
    # 放在最前面，避免被趋势/describe 吃掉
    # ---------------------------------------------------------
    if any(k in q for k in ["总和", "合计", "总计"]) or any(k in q for k in ["sum", "total"]):
        # 优先：命中到的数值列（更聪明）
        values = matched_numeric

        # 次优：问题里直接提到列名（英文列名常见）
        if not values:
            mentioned = _mentioned_cols(df, question)
            values = [c for c in mentioned if c in num_cols]

        # 兜底：随便选一个数值列
        if not values and num_cols:
            values = [num_cols[0]]

        # 没数值列就只能 describe
        if not values:
            return [ToolCall("profile", {}), ToolCall("describe", {})]

        return [
            ToolCall("profile", {}),
            ToolCall("sum_numeric", {"cols": values}),
        ]

    # ---------------------------------------------------------
    # ✅ 规则 1：趋势 / 走势 / trend
    # ---------------------------------------------------------
    if any(k in q for k in ["趋势", "走势", "trend"]):
        t = _pick_time_col(cols)
        values = matched_numeric or (num_cols[:1] if num_cols else [])

        if t and values:
            return [
                ToolCall("groupby_sum", {"group_col": t, "value_cols": values}),
                ToolCall("sort_time", {"by": t}),
                ToolCall("chart_line", {"x_col": t, "y_cols": values, "max_points": 200}),
                ToolCall("head", {"n": 20}),
            ]

        # ✅ 没时间列也不要退化：按 index 画
        if values:
            return [
                ToolCall("chart_line_index", {"y_cols": values, "max_points": 200}),
                ToolCall("head", {"n": 20}),
            ]

        return [ToolCall("describe", {})]

    # ---------------------------------------------------------
    # 规则 2：最大/最小/均值 ——先 describe
    # ---------------------------------------------------------
    if any(k in q for k in ["最大", "最小", "均值", "平均", "max", "min", "mean", "avg"]):
        return [ToolCall("describe", {})]

    # 默认：profile + describe
    return [ToolCall("profile", {}), ToolCall("describe", {})]
