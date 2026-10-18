"""합성 주문표를 만든다 — README 예시용. 실제 고객 데이터가 아니다.  python3 examples/make_sample.py
모양: 한 번 산 손님 75% · 반복 구매자는 30~120일 간격 · 활동은 기준일(2026-01-01) 앞 1년에 몰림."""
import pathlib

import numpy as np
import pandas as pd

rng = np.random.default_rng(42); rows = []
AS_OF = pd.Timestamp("2026-01-01")
for u in range(2000):
    k = 1 if rng.random() < 0.75 else int(rng.integers(2, 9))
    last = AS_OF - pd.Timedelta(days=int(rng.gamma(2.0, 60)))            # 마지막 구매는 기준일 가까이 몰림
    gaps = rng.integers(30, 120, size=k - 1) if k > 1 else []
    dates = [last - pd.Timedelta(days=int(sum(gaps[i:]))) for i in range(k - 1)] + [last]
    for j, d in enumerate(dates):
        rows.append((f"c{u:04d}", f"c{u:04d}-{j}", d.date().isoformat(), round(float(rng.gamma(2.2, 140)), 2)))
df = pd.DataFrame(rows, columns=["user", "order_id", "order_dt", "amount"]).sort_values(["order_dt", "user"])
out = pathlib.Path(__file__).with_name("sample_orders.csv"); df.to_csv(out, index=False)
print(out, len(df), "rows", df["user"].nunique(), "users")
