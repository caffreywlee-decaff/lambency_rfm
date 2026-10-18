"""블로그 글의 스무 줄 코드와 이 패키지가 같은 등급을 내는지 — 글이 있는 환경에서만 돈다(공개 리포엔 글이 없으니 건너뜀).
한 사실은 한 곳에: 글의 코드가 바뀌면 여기서 걸린다."""
import pathlib
import re
import sys

import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lambency_rfm import core  # noqa: E402
from test_core import synth  # noqa: E402

ARTICLE = pathlib.Path(__file__).resolve().parents[2] / "lambency_site/blog/research/20편_초고_한국어.md"


@pytest.mark.skipif(not ARTICLE.exists(), reason="블로그 원고 없음(공개 리포)")
def test_same_segments_as_article_code():
    code = re.search(r"```python\n(.*?)```", ARTICLE.read_text(encoding="utf-8"), re.S).group(1)
    ns = {}; exec(code, ns)  # noqa: S102 — 우리 글의 코드
    o = synth(2000, seed=7); T = pd.Timestamp("2026-01-01")
    a = ns["rfm"](o, T)["segment"]
    b = core.score(o, T)["segment"]
    assert (a.sort_index() == b.sort_index()).all()
