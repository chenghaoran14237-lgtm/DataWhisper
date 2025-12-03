from __future__ import annotations

from typing import Any

import pandas as pd

from .registry import ToolResult

import re



def _df_preview(df: pd.DataFrame, n: int = 15) -> str:
    if df is None:
        return "<none>"
    if df.empty:
        return "<empty df>"
    return df.head(n).to_string(index=False)


def tool_profile(df: pd.DataFrame) -> ToolResult:
    rows, cols = int(df.shape[0]), int(df.shape[1])
    cols_list = [str(c) for c in df.columns.tolist()]
    return ToolResult(
        kind="json",
        value={"rows": rows, "cols": cols, "columns": cols_list},
        preview=f"rows={rows}, cols={cols}, columns={cols_list[:8]}",
    )


def tool_describe(df: pd.DataFrame) -> ToolResult:
    desc = df.describe(include="all").fillna("")
    text = desc.to_string()[:1500]
    return ToolResult(kind="text", value=text, preview=text[:250])


import pandas as pd

def tool_groupby_sum(df: pd.DataFrame, group_col: str, value_cols: list[str]) -> ToolResult:
    # 参数校验
    if group_col not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: group_col not found: {group_col}", preview="group_col missing")
    for c in value_cols:
        if c not in df.columns:
            return ToolResult(kind="text", value=f"ERROR: value_col not found: {c}", preview="value_col missing")

    # 只保留需要的列，避免无关列干扰
    tmp = df[[group_col] + value_cols].copy()

    # ✅ 强制转数值：转不了就 NaN
    for c in value_cols:
        tmp[c] = pd.to_numeric(tmp[c], errors="coerce")

    g = tmp.groupby(group_col, as_index=False)

    # ✅ sum + count 配合：避免“全 NaN 的组”被 sum 成 0
    sum_df = g[value_cols].sum()     # NaN 会被跳过
    cnt_df = g[value_cols].count()   # count 不包含 NaN

    # ✅ 若某组该列 count==0，说明全部缺失，把 sum 的 0 改回缺失
    for c in value_cols:
        mask_all_missing = cnt_df[c] == 0
        sum_df.loc[mask_all_missing, c] = pd.NA

    return ToolResult(kind="table", value=sum_df, preview=_df_preview(sum_df))


def tool_groupby_mean(df: pd.DataFrame, group_col: str, value_cols: list[str]) -> ToolResult:
    if group_col not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: group_col not found: {group_col}", preview="group_col missing")
    for c in value_cols:
        if c not in df.columns:
            return ToolResult(kind="text", value=f"ERROR: value_col not found: {c}", preview="value_col missing")

    g = df.groupby(group_col)[value_cols].mean(numeric_only=True).reset_index()
    return ToolResult(kind="table", value=g, preview=_df_preview(g))


def tool_sort(df: pd.DataFrame, by: str, ascending: bool = False) -> ToolResult:
    if by not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: sort key not found: {by}", preview="sort key missing")
    out = df.sort_values(by=by, ascending=ascending)
    return ToolResult(kind="table", value=out, preview=_df_preview(out))


def tool_head(df: pd.DataFrame, n: int = 10) -> ToolResult:
    out = df.head(int(n))
    return ToolResult(kind="table", value=out, preview=_df_preview(out, n=min(15, int(n))))


def tool_pick_top1(df: pd.DataFrame, key_col: str) -> ToolResult:
    if df.empty:
        return ToolResult(kind="text", value="ERROR: empty result table", preview="empty")
    if key_col not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: key_col not found: {key_col}", preview="key_col missing")
    row = df.iloc[0].to_dict()
    return ToolResult(kind="json", value=row, preview=str(row)[:250])


def tool_sum_numeric(df: pd.DataFrame, cols: list[str] | None = None) -> ToolResult:
    if cols:
        for c in cols:
            if c not in df.columns:
                return ToolResult(kind="text", value=f"ERROR: col not found: {c}", preview="col missing")
        target = df[cols]
    else:
        target = df

    s = target.sum(numeric_only=True).to_dict()
    text = "\n".join([f"- {k}: {v}" for k, v in s.items()]) or "没有可求和的数值列。"
    return ToolResult(kind="text", value=text, preview=text[:250])

def _month_to_num(val: str):
    s = str(val).strip().lower()
    m = {
        "jan": 1, "january": 1,
        "feb": 2, "february": 2,
        "mar": 3, "march": 3,
        "apr": 4, "april": 4,
        "may": 5,
        "jun": 6, "june": 6,
        "jul": 7, "july": 7,
        "aug": 8, "august": 8,
        "sep": 9, "sept": 9, "september": 9,
        "oct": 10, "october": 10,
        "nov": 11, "november": 11,
        "dec": 12, "december": 12,
    }
    if s in m:
        return m[s]
    mm = re.match(r"^(\d{1,2})\s*月$", s)
    if mm:
        n = int(mm.group(1))
        if 1 <= n <= 12:
            return n
    if s.isdigit():
        n = int(s)
        if 1 <= n <= 12:
            return n
    return None


def tool_sort_time(df: pd.DataFrame, by: str) -> ToolResult:
    if by not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: sort key not found: {by}", preview="sort key missing")

    col = df[by]

    # 1) 先尝试 datetime
    try:
        dt = pd.to_datetime(col, errors="coerce")
        if dt.notna().mean() > 0.6:
            out = df.assign(__t=dt).sort_values("__t").drop(columns="__t")
            return ToolResult(kind="table", value=out, preview=_df_preview(out))
    except Exception:
        pass

    # 2) 再尝试月份映射（Jan/Feb/… 或 1月）
    try:
        mapped = col.map(_month_to_num)
        if mapped.notna().mean() > 0.6:
            out = df.assign(__t=mapped).sort_values("__t").drop(columns="__t")
            return ToolResult(kind="table", value=out, preview=_df_preview(out))
    except Exception:
        pass

    # 3) 退回普通排序
    out = df.sort_values(by=by, ascending=True)
    return ToolResult(kind="table", value=out, preview=_df_preview(out))

def tool_chart_line(
    df: pd.DataFrame,
    x_col: str,
    y_cols: list[str],
    max_points: int = 200,
) -> ToolResult:
    # 参数校验
    if x_col not in df.columns:
        return ToolResult(kind="text", value=f"ERROR: x_col not found: {x_col}", preview="x_col missing")
    for c in y_cols:
        if c not in df.columns:
            return ToolResult(kind="text", value=f"ERROR: y_col not found: {c}", preview="y_col missing")

    # 截断点数（但不做 dropna！）
    d = df[[x_col] + y_cols].copy().head(max_points)

    # x：保留所有点；缺失则 None；其余转成 str（稳定）
    xs_raw = d[x_col].tolist()
    xs = [None if pd.isna(v) else str(v) for v in xs_raw]

    series = []
    for c in y_cols:
        ys_raw = pd.to_numeric(d[c], errors="coerce").tolist()
        ys = [None if (v is None or (isinstance(v, float) and pd.isna(v))) else float(v) for v in ys_raw]
        series.append({"name": str(c), "values": ys})

    # 如果所有 y 全是 None，就没必要画了
    if all(all(v is None for v in s["values"]) for s in series):
        return ToolResult(kind="text", value="ERROR: all series values are missing", preview="all missing")

    spec = {
        "type": "line",
        "x": {"name": str(x_col), "values": xs},
        "series": series,
    }
    return ToolResult(kind="chart", value=spec, preview=f"line x={x_col} y={y_cols}")



def tool_chart_line_index(df: pd.DataFrame, y_cols: list[str], max_points: int = 200) -> ToolResult:
    for c in y_cols:
        if c not in df.columns:
            return ToolResult(kind="text", value=f"ERROR: y_col not found: {c}", preview="y_col missing")

    n = min(len(df), max_points)
    x = list(range(1, n + 1))

    series = []
    for c in y_cols:
        ys = pd.to_numeric(df[c], errors="coerce").tolist()[:n]
        ys = [None if (v is None or (isinstance(v, float) and pd.isna(v))) else float(v) for v in ys]
        series.append({"name": str(c), "values": ys})

    spec = {
        "type": "line",
        "x": {"name": "index", "values": x},
        "series": series,
    }
    return ToolResult(kind="chart", value=spec, preview=f"line chart by index: series={[s['name'] for s in series]}")
