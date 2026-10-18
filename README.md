# lambency_rfm

**주문 CSV 를 넣으면 가중 RFM 등급 · 고객 구조의 모양 · 두 시점 전이표를 돌려주는 작은 MCP / CLI.**
*A small MCP + CLI: paid orders in, weighted-RFM segments, customer-base shape and a transition matrix out. Every knob is a parameter.*

> 계산은 Lambency 블로그 «더 새롭고 더 무거운 모델이 답을 주지는 않는다»에 적은 그대로입니다. 글의 스무 줄 코드와 이 패키지가 같은 등급을 내는지 시험이 확인합니다.
> 데이터는 쓰는 사람 컴퓨터 안에서만 돕니다. 서버는 아무것도 밖으로 보내지 않습니다.

---

## 왜 (Why)

RFM 은 누구나 돌립니다. 그런데 흔한 방식은 R·F·M 을 각각 5등급으로 잘라 조합을 만드는데, 실제 고객 데이터에서는 대부분이
한 번만 사서 F 가 한 칸이 됩니다. 이 도구는 세 값을 브랜드 안 백분위로 바꾼 뒤 **무게를 달아 하나로 합치고**, 규칙(큰손 · 잠든 · 신규)을
먼저 적용한 다음 구간표로 등급을 나눕니다. 무게 · F 블렌드 · 잠든 배수 · 구간표(칸 수와 경계) · 신규 일수가 전부 파라미터라, 브랜드에
맞게 모양을 조절할 수 있습니다. 두 날짜를 주면 **누가 어디서 어디로 갔는지** 전이표까지 나옵니다.

## 설치 (Install)

```bash
git clone https://github.com/caffreywlee-decaff/lambency_rfm.git && cd lambency_rfm
pip install -e .                 # CLI 명령 `lambency-rfm`
pip install "mcp[cli]"           # MCP 서버도 쓸 때
python3 examples/make_sample.py  # 합성 예시 주문표 (실데이터 아님)
```

## 입력 (Input)

CSV 네 컬럼. 컬럼 이름이 다르면 `--user-col` 등으로 알려 줍니다.

| 컬럼 | 뜻 |
|---|---|
| `user` | 고객 한 명 (채널마다 갈린 회원은 **먼저** 묶어 두세요) |
| `order_id` | 주문서 한 장 (상품 줄이 아니라) |
| `order_dt` | 주문일 |
| `amount` | 결제 금액, 한 통화 (취소·반품은 빼고) |

🔴 **결제가 끝난 주문만 · 주문서 한 장 · 한 통화 · user 는 정말 한 사람.** 이 네 가지는 도구가 해 주지 않습니다. 결제 시도나 취소 주문이 섞이면
산 적 없는 사람이 자주 사는 손님이 되고, 통화가 섞이면 등급표 맨 위가 허상이 됩니다.

## CLI

```bash
lambency-rfm score   examples/sample_orders.csv --as-of 2026-01-01
lambency-rfm score   examples/sample_orders.csv --as-of 2026-01-01 --weights 0.2,0.3,0.5 --dormant-x 3 --out my_segments.csv
lambency-rfm migrate examples/sample_orders.csv --t1 2025-07-01 --t2 2026-01-01
lambency-rfm score   orders.csv --as-of 2026-01-01 --cuts "0.8:Gold,0.5:Silver,0.2:Bronze"   # 구간표를 세 칸으로
```

출력은 JSON 입니다. `score` 는 등급별 인원 · 평균 재구매 주기 · 큰손 기준 금액 · 상위/중간/하위 비율과 모양(Diamond · Pyramid ·
Inverted · Hourglass). `migrate` 는 t1 의 각 등급이 t2 에 어디로 갔는지(%) · 그대로 남은 비율 · 잠든으로 간 비율 · 그 사이 구매율.
`--out` 을 주면 고객별 결과를 CSV 로 저장합니다(리포에 올리지 마세요 — `.gitignore` 가 `*_segments.csv` 를 막습니다).

## 파라미터 (Parameters)

| 파라미터 | 기본 | 바꾸면 |
|---|---|---|
| `--weights` R,F,M | `0.1,0.2,0.7` | M 에 실을수록 위 칸이 커지고 허리가 두꺼워진다. 맞히는 힘보다 **모양과 VIP 칸 크기**를 고르는 손잡이 |
| `--blend` | `0.5` | F 안에서 '몇 번'의 비중. 나머지는 '얼마나 자주'(평균 간격) |
| `--dormant-x` | `2` | 잠든 기준 = 평균 재구매 주기 × 배수. 날짜로 고정하지 않는다. 브랜드마다 맞출 것 |
| `--new-days` | `60` | 한 번 샀고 첫 구매가 이 안이면 신규 |
| `--top-pct` | `0.99` | 누적 금액 이 분위 이상은 점수와 상관없이 최상위 (리셀러가 여기 들어올 수 있다) |
| `--cuts` | 7칸 | `경계:이름,...` 내림차순. 칸 수와 경계를 바꿀 수 있다. 마지막 경계 아래는 Hibernate |
| `--min-gap-days` | `0` | 재구매 주기 평균에서 이보다 짧은 간격(분할 결제·추가 주문)은 뺀다 |

기본 7칸: `0.9:Champions, 0.8:Loyal Customers, 0.6:Potential Loyalists, 0.4:Promising, 0.2:Need Attention, 0.1:At Risk`, 그 아래 `Hibernate`.
모양은 상위(Champions · Loyal) · 중간(Potential · Need Attention · At Risk) · 하위(Promising · Hibernate)로 묶어 봅니다(신규 제외).
구간표 이름을 바꾸면 이름 순서대로 3등분해 묶고, 그렇게 했다고 출력에 적습니다.

## MCP 로 쓰기 (Claude Code · Claude Desktop · Cursor)

```bash
claude mcp add lambency_rfm -- python3 -m lambency_rfm.server
```

```json
{ "mcpServers": { "lambency_rfm": { "command": "python3", "args": ["-m", "lambency_rfm.server"] } } }
```

도구 셋: `rfm_score(orders_csv, as_of, weights=..., blend=..., dormant_x=..., cuts=..., out_csv=...)` ·
`rfm_migrate(orders_csv, t1, t2, ...)` · `rfm_params()`. 이렇게 물으면 됩니다.

- *"orders.csv 로 2026-03-06 기준 RFM 돌려 줘. 무게는 0.2,0.3,0.5 로."*
- *"같은 파일로 2025-12-06 → 2026-03-06 전이표 뽑고, 최상위에서 잠든으로 간 비율 알려 줘."*
- *"구간표를 Gold/Silver/Bronze 세 칸으로 바꾸면 모양이 어떻게 되나?"*

## 한계 (Limits)

- **고객을 묶어 주지 않습니다.** 자사몰 회원과 플랫폼 구매자가 같은 사람인지는 넣기 전에 정해야 합니다.
- **주문을 걸러 주지 않습니다.** 결제 시도 · 취소 · 반품 · 통화 섞임은 넣기 전에 정리합니다.
- **리셀러를 거르지 않습니다.** 수량 데이터가 없어서입니다. M 에 무게를 많이 주면 대량 구매 계정이 최상위에 올라옵니다 — 수량으로 따로 보세요.
- 등급 차이는 반응 차이이지 효과가 아닙니다. 등급별로 보냈더니 늘었는지는 따로 실험해야 압니다.

## 테스트

```bash
python3 -m pytest tests -q      # 순수 로직 · 합성 데이터
```

## Quick start (English)

```bash
pip install -e . && python3 examples/make_sample.py
lambency-rfm score   examples/sample_orders.csv --as-of 2026-01-01 --weights 0.1,0.2,0.7 --blend 0.5 --dormant-x 2
lambency-rfm migrate examples/sample_orders.csv --t1 2025-07-01 --t2 2026-01-01
claude mcp add lambency_rfm -- python3 -m lambency_rfm.server
```

Input: a CSV of **paid** orders (`user, order_id, order_dt, amount`), one row per order, one currency, one row-owner per real customer.
R, F, M are percentile-ranked within the file, F blends count and inter-purchase interval, the three are combined with weights (default 0.1/0.2/0.7),
rules come first (top spenders → Champions, last purchase older than cycle × `dormant_x` → Hibernate, single recent purchase → New), then cut-offs.
`migrate` runs the same parameters at two dates and returns where each segment went. Nothing leaves your machine.

## 만든 곳 (About)

[Lambency](https://lambency-data.github.io/)(데이터 · AI 컨설팅). 고객을 한 사람으로 묶고, 주문표에서 무엇을 구매로 셀지 정하는 일 — 이 도구가
해 주지 않는 그 앞 단계 — 를 그 회사 데이터에 맞게 하는 것이 저희 일입니다. 문의 caffrey.w.lee@gmail.com

## 라이선스

MIT.
