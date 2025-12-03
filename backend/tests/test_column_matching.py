import pandas as pd
from app.services.planner import _match_cols


def test_match_cols_completion_rate_synonym():
    df = pd.DataFrame(columns=["任务点完成百分比", "课程视频进度", "班级", "分组"])
    cols = list(df.columns)

    m = _match_cols("按任务点完成率给出趋势图", cols)
    assert "任务点完成百分比" in m

