"""CLI.

  lambency-rfm score   orders.csv --as-of 2026-03-06                       # 등급 요약 + 모양 (JSON)
  lambency-rfm score   orders.csv --as-of 2026-03-06 --out my_segments.csv  # 고객별 등급을 CSV 로도
  lambency-rfm migrate orders.csv --t1 2025-12-06 --t2 2026-03-06          # 전이표
  공통 파라미터: --weights 0.1,0.2,0.7 --blend 0.5 --dormant-x 2 --new-days 60 --top-pct 0.99
               --cuts "0.9:Champions,0.8:Loyal Customers,0.6:Potential Loyalists,0.4:Promising,0.2:Need Attention,0.1:At Risk"
               --min-gap-days 7   (평균 재구매 주기를 낼 때 이보다 짧은 간격은 뺀다)
               --user-col --order-col --date-col --amount-col   (CSV 컬럼 이름이 다를 때)
"""
import argparse
import json
import sys

from . import core


def _common(p):
    p.add_argument("orders", help="주문 CSV — 결제가 끝난 주문만, 한 줄 = 주문서 한 장, 한 통화")
    p.add_argument("--weights", default="0.1,0.2,0.7", help="R,F,M 무게 (합 1)")
    p.add_argument("--blend", type=float, default=0.5, help="F 안에서 횟수의 비중 (나머지는 구매 간격)")
    p.add_argument("--dormant-x", type=float, default=2.0, help="잠든 기준 = 평균 재구매 주기 × 이 배수")
    p.add_argument("--new-days", type=int, default=60, help="한 번 샀고 이 일수 안이면 신규")
    p.add_argument("--top-pct", type=float, default=0.99, help="누적 금액 이 분위 이상은 무조건 최상위")
    p.add_argument("--cuts", default="", help="구간표 '경계:이름,...' 내림차순. 비우면 7칸 기본값")
    p.add_argument("--min-gap-days", type=int, default=0, help="재구매 주기 평균에서 이보다 짧은 간격 제외")
    for c in ("user", "order", "date", "amount"):
        p.add_argument(f"--{c}-col", default={"user": "user", "order": "order_id", "date": "order_dt", "amount": "amount"}[c])
    p.add_argument("--out", default="", help="고객별 결과를 이 CSV 로 저장 (리포에 올리지 말 것)")


def _params(a):
    return dict(weights=a.weights, blend=a.blend, dormant_x=a.dormant_x, new_days=a.new_days, top_pct=a.top_pct,
                cuts=a.cuts, min_gap_days=a.min_gap_days)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="lambency-rfm", description="주문 CSV → 가중 RFM 등급 · 모양 · 전이표 (파라미터 전부 열림)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p1 = sub.add_parser("score", help="한 시점 등급과 모양"); _common(p1)
    p1.add_argument("--as-of", required=True, help="기준일 YYYY-MM-DD (이 날까지의 주문만)")
    p2 = sub.add_parser("migrate", help="두 시점 전이표"); _common(p2)
    p2.add_argument("--t1", required=True); p2.add_argument("--t2", required=True)
    a = ap.parse_args(argv)
    try:
        orders = core.load_orders(a.orders, a.user_col, a.order_col, a.date_col, a.amount_col)
        if a.cmd == "score":
            g = core.score(orders, a.as_of, **_params(a))
            out = core.summarize(g)
            if a.out:
                g.reset_index().to_csv(a.out, index=False); out["saved"] = a.out
        else:
            out, j = core.migrate(orders, a.t1, a.t2, **_params(a))
            if a.out:
                j.reset_index().to_csv(a.out, index=False); out["saved"] = a.out
        out["dropped_rows"] = orders.attrs.get("dropped_rows", 0)
    except (ValueError, FileNotFoundError) as e:
        print(f"오류: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
