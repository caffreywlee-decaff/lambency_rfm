"""MCP 서버. 에이전트(Claude Code · Cursor 등)가 아래 도구를 부른다.

  pip install "mcp[cli]"
  python -m lambency_rfm.server        # stdio

도구:
  rfm_score(orders_csv, as_of, ...)      한 시점 등급 요약 + 모양 (+ out_csv 로 고객별 저장)
  rfm_migrate(orders_csv, t1, t2, ...)   두 시점 전이표 (+ out_csv 로 고객별 from/to 저장)
  rfm_params()                           파라미터가 각각 무엇을 바꾸는지
데이터는 쓰는 사람 컴퓨터 안에서만 돈다. 서버는 아무것도 밖으로 보내지 않는다.
"""
from . import core

try:                                   # mcp 1.x
    from mcp.server.fastmcp import FastMCP
except ImportError:
    try:                               # mcp 2.x — FastMCP 가 MCPServer 로 이름이 바뀌었다 (2026-10-18 실측, mcp 2.3.0)
        from mcp.server import MCPServer as FastMCP
    except ImportError as e:  # noqa: BLE001
        raise SystemExit('mcp 패키지가 필요합니다: pip install "mcp[cli]"  (서버 없이 CLI 만 쓰려면 python -m lambency_rfm.cli)') from e

mcp = FastMCP("lambency_rfm")


def _run(orders_csv, user_col, order_col, date_col, amount_col):
    return core.load_orders(orders_csv, user_col, order_col, date_col, amount_col)


@mcp.tool()
def rfm_score(orders_csv: str, as_of: str, weights: str = "0.1,0.2,0.7", blend: float = 0.5, dormant_x: float = 2.0,
              new_days: int = 60, top_pct: float = 0.99, cuts: str = "", min_gap_days: int = 0, out_csv: str = "",
              user_col: str = "user", order_col: str = "order_id", date_col: str = "order_dt", amount_col: str = "amount") -> dict:
    """주문 CSV(결제 끝난 주문만 · 한 줄 = 주문서 한 장 · 한 통화)로 as_of 기준 가중 RFM 등급을 만든다.
    weights 'R,F,M'(합 1) · blend = F 안의 횟수 비중 · dormant_x = 평균 재구매 주기 배수 · new_days · top_pct ·
    cuts '경계:이름,...'(비우면 7칸 기본). 돌려주는 건 등급별 인원과 상위·중간·하위 모양. out_csv 를 주면 고객별 등급도 저장."""
    try:
        o = _run(orders_csv, user_col, order_col, date_col, amount_col)
        g = core.score(o, as_of, weights=weights, blend=blend, dormant_x=dormant_x, new_days=new_days, top_pct=top_pct,
                       cuts=cuts, min_gap_days=min_gap_days)
        out = core.summarize(g)
        if out_csv:
            g.reset_index().to_csv(out_csv, index=False); out["saved"] = out_csv
        out["dropped_rows"] = o.attrs.get("dropped_rows", 0)
        return out
    except (ValueError, FileNotFoundError) as e:
        return {"error": str(e)}


@mcp.tool()
def rfm_migrate(orders_csv: str, t1: str, t2: str, weights: str = "0.1,0.2,0.7", blend: float = 0.5, dormant_x: float = 2.0,
                new_days: int = 60, top_pct: float = 0.99, cuts: str = "", min_gap_days: int = 0, out_csv: str = "",
                user_col: str = "user", order_col: str = "order_id", date_col: str = "order_dt", amount_col: str = "amount") -> dict:
    """같은 파라미터로 t1·t2 두 시점을 돌려 전이표를 만든다: t1 의 각 등급이 t2 에 어디로 갔는지(%), 그대로 남은 비율,
    잠든으로 간 비율, 그 사이 구매한 비율, 위·아래로 움직인 인원. out_csv 를 주면 고객별 from/to 를 저장한다."""
    try:
        o = _run(orders_csv, user_col, order_col, date_col, amount_col)
        out, j = core.migrate(o, t1, t2, weights=weights, blend=blend, dormant_x=dormant_x, new_days=new_days, top_pct=top_pct,
                              cuts=cuts, min_gap_days=min_gap_days)
        if out_csv:
            j.reset_index().to_csv(out_csv, index=False); out["saved"] = out_csv
        out["dropped_rows"] = o.attrs.get("dropped_rows", 0)
        return out
    except (ValueError, FileNotFoundError) as e:
        return {"error": str(e)}


@mcp.tool()
def rfm_params() -> dict:
    """각 파라미터가 무엇을 바꾸는지와 기본값."""
    return {
        "weights": "R,F,M 무게. 합 1. M 에 실을수록 위 칸이 커지고 허리가 두꺼워진다. 기본 0.1,0.2,0.7 (패션: F 작고 R 은 브랜드 의견으로 조금)",
        "blend": "F 안에서 '몇 번'의 비중. 나머지는 '얼마나 자주'(평균 간격). 기본 0.5",
        "dormant_x": "잠든 기준 = 평균 재구매 주기 × 배수. 날짜로 고정하지 않는다. 기본 2 (브랜드마다 맞출 것)",
        "new_days": "한 번 샀고 첫 구매가 이 일수 안이면 신규. 기본 60",
        "top_pct": "누적 금액이 이 분위 이상이면 점수와 상관없이 최상위. 기본 0.99 (리셀러가 여기 들어올 수 있다)",
        "cuts": "점수 구간표 '경계:이름,...'. 기본 7칸: " + ",".join(f"{v}:{l}" for v, l in core.DEFAULT_CUTS) + " / 그 아래 Hibernate",
        "min_gap_days": "평균 재구매 주기를 낼 때 이보다 짧은 간격(분할 결제·추가 주문)은 뺀다. 기본 0",
        "입력": "결제가 끝난 주문만 · 한 줄 = 주문서 한 장 · 한 통화 · user 는 정말 한 사람. 이 네 가지는 도구가 해 주지 않는다",
    }


def main():
    mcp.run()


if __name__ == "__main__":
    main()
