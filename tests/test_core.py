"""순수 로직 시험 — 합성 주문만 쓴다. 네트워크·실데이터 없음.  python3 -m pytest tests -q"""
import pathlib
import sys

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from lambency_rfm import core  # noqa: E402


def synth(n_users=3000, seed=1):
    rng = np.random.default_rng(seed); rows = []
    for u in range(n_users):
        k = 1 if rng.random() < 0.8 else int(rng.integers(2, 8))
        for j in range(k):
            rows.append((f"u{u}", f"u{u}-{j}", pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 700))), float(rng.gamma(2, 150))))
    return pd.DataFrame(rows, columns=["user", "order_id", "order_dt", "amount"])


ORDERS = synth()
T = "2026-01-01"


def test_scores_in_unit_range_and_segments_complete():
    g = core.score(ORDERS, T)
    assert g["score"].between(0, 1).all()
    assert set(g["segment"]) <= set(core.DEFAULT_TIERS["top"] + core.DEFAULT_TIERS["mid"] + core.DEFAULT_TIERS["bot"] + [core.NEW])
    assert len(g) == ORDERS["user"].nunique()


def test_rule_precedence_top_spender_beats_everything():
    g = core.score(ORDERS, T)
    top = g[g["M"] >= g.attrs["top_cut"]]
    assert (top["segment"] == "Champions").all()


def test_dormant_rule_uses_cycle_times_x():
    g = core.score(ORDERS, T, dormant_x=2)
    cyc = g.attrs["cycle_days"]
    late = g[(g["R"] > cyc * 2) & (g["M"] < g.attrs["top_cut"])]
    assert (late["segment"] == core.DORMANT).all()
    # 배수를 올리면 잠든 비중이 내려간다
    assert (core.score(ORDERS, T, dormant_x=4)["segment"] == core.DORMANT).mean() < (g["segment"] == core.DORMANT).mean()


def test_new_rule():
    g = core.score(ORDERS, T, new_days=60)
    new = g[(g["n"] == 1) & (g["R"] <= 60) & (g["M"] < g.attrs["top_cut"])]
    assert (new["segment"] == core.NEW).all()


def test_weights_change_top_tier_size():
    a = core.shape(core.score(ORDERS, T, weights=(1 / 3, 1 / 3, 1 / 3)))
    b = core.shape(core.score(ORDERS, T, weights=(0.1, 0.2, 0.7)))
    assert a["top_pct"] != b["top_pct"]


def test_custom_cuts_and_tiers_note():
    g = core.score(ORDERS, T, cuts="0.8:Gold,0.5:Silver,0.2:Bronze")
    assert set(g["segment"]) <= {"Gold", "Silver", "Bronze", core.DORMANT, core.NEW}
    s = core.shape(g)
    assert "note" in s and s["tiers"]["top"] == ["Gold"]


def test_shape_rules_on_handmade_tiers():
    def mk(top, mid, bot):
        seg = ["Champions"] * top + ["Potential Loyalists"] * mid + ["Promising"] * bot
        df = pd.DataFrame({"segment": seg}); df.attrs["params"] = {"cuts": None}
        return core.shape(df)["shape"]
    assert mk(10, 50, 40) == "Diamond"
    assert mk(10, 30, 60) == "Pyramid"
    assert mk(60, 30, 10) == "Inverted"
    assert mk(40, 20, 40) == "Hourglass"


def test_bad_params_raise():
    with pytest.raises(ValueError):
        core.score(ORDERS, T, weights=(0.5, 0.5, 0.5))
    with pytest.raises(ValueError):
        core.parse_cuts("0.9:A,0.9:B")
    with pytest.raises(ValueError):
        core.parse_cuts("0.9:Hibernate")
    with pytest.raises(ValueError):
        core.score(ORDERS, "2000-01-01")


def test_migrate_rows_sum_to_100_and_counts_match():
    s, j = core.migrate(ORDERS, "2025-07-01", "2026-01-01")
    for r in s["rows"]:
        assert abs(sum(r["to_pct"].values()) - 100) < 0.2
    assert sum(s["moved"].values()) == s["n_t1"] == len(j)
    assert s["t1"] == "2025-07-01"


def test_load_orders_with_renamed_columns(tmp_path):
    p = tmp_path / "o.csv"
    ORDERS.rename(columns={"user": "member_id", "amount": "paid"}).to_csv(p, index=False)
    o = core.load_orders(p, user_col="member_id", amount_col="paid")
    assert list(o.columns) == list(core.COLS) and len(o) == len(ORDERS)
