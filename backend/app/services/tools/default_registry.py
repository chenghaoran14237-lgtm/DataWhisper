from app.services.tools.registry import ToolRegistry
from app.services.tools import pandas_tools as pt  # 按你实际 import 路径调整

def build_default_registry() -> ToolRegistry:
    r = ToolRegistry()  # ✅ 每次新建，绝不会重复注册

    # 下面是示例：按你原来的工具一个个 register
    r.register("profile", pt.tool_profile)
    r.register("describe", pt.tool_describe)
    r.register("head", pt.tool_head)
    r.register("sum_numeric", pt.tool_sum_numeric)
    r.register("groupby_sum", pt.tool_groupby_sum)
    r.register("sort_time", pt.tool_sort_time)
    r.register("chart_line", pt.tool_chart_line)

    # ✅ 新增的兜底趋势图
    r.register(
        "chart_line_index",
        lambda df, y_cols, max_points=200, **kw: pt.tool_chart_line_index(
            df, y_cols=y_cols, max_points=max_points
        ),
    )

    return r
