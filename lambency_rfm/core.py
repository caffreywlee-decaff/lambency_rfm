"""가중 RFM — 계산은 한 곳(여기)에만 있다. CLI 와 MCP 서버는 이 함수를 부른다.

순서 (Lambency 블로그 «더 새롭고 더 무거운 모델이 답을 주지는 않는다» 의 05~11 과 같다):
  1. 고객별 R(마지막 구매 뒤 일수) · n(주문 수) · M(누적 금액) · gap(평균 구매 간격)
  2. F = blend × 횟수(0~1) + (1−blend) × 간격(0~1, 짧을수록 높게)
  3. R·F·M 각각을 브랜드 안 백분위(0~1)로 → 종합 점수 = w_R·R + w_F·F + w_M·M
  4. 규칙 먼저: 쓴 돈 상위(top_pct) → 최상위 · 마지막 구매가 평균 재구매 주기 × dormant_x 보다 오래 → 잠든 ·
     한 번 샀고 첫 구매가 new_days 안 → 신규. 나머지는 cuts 구간표.
  5. 상위·중간·하위 세 칸으로 묶어 모양(다이아몬드·피라미드·역피라미드·모래시계)
  6. 두 시점으로 돌려 겹치면 전이표

입력 주문표는 **결제가 끝난 주문만, 한 줄 = 주문서 한 장, 한 통화** 여야 한다. 그건 이 코드가 해 주지 않는다.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

DEFAULT_WEIGHTS = (0.1, 0.2, 0.7)
DEFAULT_CUTS = [(0.9, "Champions"), (0.8, "Loyal Customers"), (0.6, "Potential Loyalists"),
                (0.4, "Promising"), (0.2, "Need Attention"), (0.1, "At Risk")]
DORMANT = "Hibernate"
NEW = "New Customer"
DEFAULT_TIERS = {"top": ["Champions", "Loyal Customers"],
                 "mid": ["Potential Loyalists", "Need Attention", "At Risk"],
                 "bot": ["Promising", "Hibernate"]}
COLS = ("user", "order_id", "order_dt", "amount")


# ───────────────────────── 입력 ─────────────────────────
def load_orders(path, user_col="user", order_col="order_id", date_col="order_dt", amount_col="amount") -> pd.DataFrame:
    """CSV → (user, order_id, order_dt, amount). 컬럼 이름이 다르면 *_col 로 알려 준다."""
    df = pd.read_csv(path, dtype={user_col: str, order_col: str})
    missing = [c for c in (user_col, order_col, date_col, amount_col) if c not in df.columns]
    if missing:
        raise ValueError(f"컬럼이 없습니다: {missing}. 있는 컬럼: {list(df.columns)}")
    o = df.rename(columns={user_col: "user", order_col: "order_id", date_col: "order_dt", amount_col: "amount"})[list(COLS)].copy()
    o["order_dt"] = pd.to_datetime(o["order_dt"], errors="coerce")
    o["amount"] = pd.to_numeric(o["amount"], errors="coerce")
    bad = int(o[list(COLS)].isna().any(axis=1).sum())
    o = o.dropna(subset=list(COLS))
    o.attrs["dropped_rows"] = bad
    return o


def parse_weights(s) -> tuple[float, float, float]:
    w = tuple(float(x) for x in (s.split(",") if isinstance(s, str) else s))
    if len(w) != 3 or any(x < 0 for x in w) or abs(sum(w) - 1) > 1e-6:
        raise ValueError(f"무게는 R,F,M 셋이고 합이 1이어야 합니다: {w}")
    return w


def parse_cuts(s) -> list[tuple[float, str]]:
    """'0.9:Champions,0.8:Loyal Customers,...' → [(0.9,'Champions'), ...] 내림차순. 마지막 미만은 잠든(DORMANT)."""
    if not s:
        return list(DEFAULT_CUTS)
    if isinstance(s, str):
        items = []
        for part in s.split(","):
            v, _, lab = part.partition(":")
            items.append((float(v), lab.strip()))
    else:
        items = [(float(v), str(lab)) for v, lab in s]
    items.sort(key=lambda x: -x[0])
    vals = [v for v, _ in items]
    if not items or any(not (0 < v < 1) for v in vals) or len(set(vals)) != len(vals) or len({l for _, l in items}) != len(items):
        raise ValueError(f"구간표는 (0,1) 사이 서로 다른 경계와 서로 다른 이름이어야 합니다: {items}")
    if any(l in (DORMANT, NEW) for _, l in items):
        raise ValueError(f"'{DORMANT}' 와 '{NEW}' 는 규칙 등급 이름이라 구간표에 쓸 수 없습니다")
    return items


# ───────────────────────── 점수 · 등급 ─────────────────────────
def _mm(s: pd.Series) -> pd.Series:
    lo, hi = s.min(), s.max()
    return (s - lo) / (hi - lo) if hi > lo else pd.Series(0.0, index=s.index)


def _pct(s: pd.Series, ascending=True) -> pd.Series:
    return s.rank(pct=True, ascending=ascending, method="average")


def score(orders: pd.DataFrame, as_of, *, weights=DEFAULT_WEIGHTS, blend=0.5, dormant_x=2.0, new_days=60,
          top_pct=0.99, cuts=None, min_gap_days=0) -> pd.DataFrame:
    """고객별 점수와 등급. index = user. attrs 에 cycle · top_cut · params."""
    w = parse_weights(weights)
    cuts = parse_cuts(cuts)
    if not (0 <= blend <= 1):
        raise ValueError("blend 는 0~1")
    if not (0 < top_pct < 1):
        raise ValueError("top_pct 는 (0,1)")
    as_of = pd.Timestamp(as_of)
    o = orders[orders["order_dt"] <= as_of]
    if o.empty:
        raise ValueError(f"{as_of.date()} 까지의 주문이 없습니다")
    g = o.groupby("user").agg(n=("order_id", "nunique"), first=("order_dt", "min"), last=("order_dt", "max"), M=("amount", "sum"))
    g["R"] = (as_of - g["last"]).dt.days
    gap = (g["last"] - g["first"]).dt.days / (g["n"] - 1).where(g["n"] > 1)
    g["gap"] = gap
    g["F_raw"] = blend * _mm(g["n"] - 1) + (1 - blend) * (1 - _mm(gap.fillna(gap.max() if gap.notna().any() else 0)))
    g["R_score"], g["F_score"], g["M_score"] = _pct(g["R"], False), _pct(g["F_raw"]), _pct(g["M"])
    g["score"] = w[0] * g["R_score"] + w[1] * g["F_score"] + w[2] * g["M_score"]

    top_cut = float(g["M"].quantile(top_pct))
    rep = gap[g["n"] > 1]
    if min_gap_days:
        rep = rep[rep >= min_gap_days]
    cycle = float(rep.mean()) if len(rep) else float("nan")

    seg = pd.Series(DORMANT, index=g.index, dtype=object)          # 구간표 맨 아래 = 잠든
    for v, lab in sorted(cuts, key=lambda x: x[0]):                  # 낮은 경계부터 덮어써서 높은 경계가 이긴다
        seg[g["score"] >= v] = lab
    seg[(g["n"] == 1) & (g["R"] <= new_days)] = NEW                   # 규칙은 뒤에 쓸수록 우선: 신규 < 잠든 < 큰손
    if np.isfinite(cycle):
        seg[g["R"] > cycle * dormant_x] = DORMANT
    seg[g["M"] >= top_cut] = cuts[0][1]
    g["segment"] = seg
    g.attrs.update({"as_of": str(as_of.date()), "cycle_days": cycle, "top_cut": top_cut, "n": int(len(g)),
                    "params": {"weights": w, "blend": blend, "dormant_x": dormant_x, "new_days": new_days,
                               "top_pct": top_pct, "cuts": cuts, "min_gap_days": min_gap_days}})
    return g


def _labels(cuts) -> list[str]:
    return [lab for _, lab in parse_cuts(cuts)] + [DORMANT]


def tiers_for(cuts=None, tiers=None) -> dict:
    """상위·중간·하위 묶음. 기본 등급명이면 블로그와 같은 묶음, 아니면 이름 순서대로 3등분(알려 준다)."""
    labels = _labels(cuts)
    if tiers:
        return tiers
    if labels == _labels(DEFAULT_CUTS):
        return DEFAULT_TIERS
    k = max(1, len(labels) // 3)
    return {"top": labels[:k], "mid": labels[k:2 * k], "bot": labels[2 * k:], "note": "custom labels: split by order into thirds"}


def shape(scored: pd.DataFrame, tiers=None) -> dict:
    t = tiers or tiers_for(scored.attrs.get("params", {}).get("cuts"))
    s = scored["segment"][scored["segment"] != NEW]
    n = int(len(s))
    top, mid, bot = (float(s.isin(t[k]).mean() * 100) if n else 0.0 for k in ("top", "mid", "bot"))
    name = ("Pyramid" if bot > mid > top else "Diamond" if (mid > bot and mid > top) else "Inverted" if top > mid > bot
            else "Hourglass" if (bot > mid and top > mid) else "Undefined")
    return {"n_excluding_new": n, "top_pct": round(top, 1), "mid_pct": round(mid, 1), "bot_pct": round(bot, 1), "shape": name,
            "tiers": {k: t[k] for k in ("top", "mid", "bot")}, **({"note": t["note"]} if "note" in t else {})}


def summarize(scored: pd.DataFrame, tiers=None) -> dict:
    labels = _labels(scored.attrs["params"]["cuts"]) + [NEW]
    vc = scored["segment"].value_counts()
    return {"as_of": scored.attrs["as_of"], "n": scored.attrs["n"], "cycle_days": _r(scored.attrs["cycle_days"]),
            "top_cut_amount": _r(scored.attrs["top_cut"]),
            "segments": [{"segment": l, "n": int(vc.get(l, 0)), "pct": round(float(vc.get(l, 0)) / scored.attrs["n"] * 100, 1)} for l in labels],
            "shape": shape(scored, tiers), "params": _jsonable(scored.attrs["params"])}


# ───────────────────────── 전이표 ─────────────────────────
def migrate(orders: pd.DataFrame, t1, t2, *, tiers=None, **params) -> tuple[dict, pd.DataFrame]:
    """같은 파라미터로 t1·t2 두 번 돌려 겹친다. (요약 dict, 고객별 from/to 표)."""
    t1, t2 = pd.Timestamp(t1), pd.Timestamp(t2)
    if t2 <= t1:
        raise ValueError("t2 는 t1 보다 뒤여야 합니다")
    g1, g2 = score(orders, t1, **params), score(orders, t2, **params)
    order = _labels(params.get("cuts")) + [NEW]
    j = g1[["segment"]].join(g2[["segment"]], lsuffix="_from", rsuffix="_to", how="left")
    j["segment_to"] = j["segment_to"].fillna("(missing)")
    bought = set(orders[(orders["order_dt"] > t1) & (orders["order_dt"] <= t2)]["user"])
    j["bought_between"] = j.index.isin(bought)
    rank = {l: i for i, l in enumerate(order)}
    j["move"] = [("new" if a == NEW else "up" if rank.get(b, 99) < rank.get(a, 99) else "down" if rank.get(b, 99) > rank.get(a, 99) else "same")
                 for a, b in zip(j["segment_from"], j["segment_to"])]
    ct = pd.crosstab(j["segment_from"], j["segment_to"]).reindex(index=order, fill_value=0)
    rows = []
    for s in order:
        n = int(ct.loc[s].sum()) if s in ct.index else 0
        if n == 0:
            continue
        to = {d: round(float(ct.loc[s, d]) / n * 100, 1) for d in ct.columns if ct.loc[s, d] > 0}
        rows.append({"from": s, "n": n, "to_pct": to, "stayed_pct": to.get(s, 0.0), "to_dormant_pct": to.get(DORMANT, 0.0),
                     "bought_between_pct": round(float(j.loc[j["segment_from"] == s, "bought_between"].mean() * 100), 1)})
    summary = {"t1": str(t1.date()), "t2": str(t2.date()), "n_t1": int(len(g1)), "n_t2": int(len(g2)),
               "shape_t1": shape(g1, tiers)["shape"], "shape_t2": shape(g2, tiers)["shape"], "rows": rows,
               "moved": {k: int((j["move"] == k).sum()) for k in ("up", "same", "down", "new")},
               "params": _jsonable(g1.attrs["params"])}
    return summary, j


# ───────────────────────── 보조 ─────────────────────────
def _r(x, nd=1):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), nd)


def _jsonable(p: dict) -> dict:
    q = dict(p)
    q["weights"] = list(q["weights"])
    q["cuts"] = [[v, l] for v, l in q["cuts"]]
    return q
