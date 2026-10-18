# lambency_rfm — 공개 RFM MCP/CLI (프로젝트 규칙)

2026-10-18 신설. 카프 «풀어도 되고 lambency_rfm 으로 하면 될듯» (블로그 20편 «더 새롭고 더 무거운 모델이 답을 주지는 않는다» 의 코드를 파라미터로 열어 공개).
옛 결정 «RFM 은 리포가 아니라 콘텐츠로»(byteme/docs/오픈소스_영향력_전략_2026-10-13.md §0)는 이 날 뒤집힘 — 글이 이미 코드를 공개하므로. 남는 값(고객 묶기 · 주문 정의 · 데이터 정리)은 이 도구가 안 한다.

## 무엇을 푸나 / 안 푸나
- 푼다: 가중 RFM 점수 · 규칙 등급 · 모양 · 전이표. 파라미터 전부(무게 · blend · dormant_x · new_days · top_pct · cuts · min_gap_days).
- 안 푼다: 고객 동일성 묶기 · 주문 정리(결제 시도·취소·통화) · 리셀러 판별 · 어떤 브랜드의 실제 파라미터 값이 아닌 «그 값을 고른 이유» 데이터.

## 🔴 공개 규칙 (커밋 전 매번)
- 실제 고객 데이터 0 · 브랜드·클라이언트·전 직장 실명 0(이 파일에도 적지 않는다 — 공개 리포에 같이 올라간다) · 키 0. 예시는 `examples/make_sample.py` 가 만든 합성 데이터만.
- `*_segments.csv` · `*_migration.csv` 는 .gitignore. 사용자가 돌린 결과는 리포에 안 들어온다.
- 계산은 `lambency_rfm/core.py` 한 곳. CLI·MCP 는 부르기만. 블로그 코드와의 동일성은 `tests/test_article_parity.py`(글이 있는 환경에서만).

## 갱신 흐름
코드 고침 → `python3 -m pytest tests -q` 전부 통과 → 커밋 → 카프 «올려» → `git push origin main` (리모트 caffreywlee-decaff/lambency_rfm, 공개).
블로그 원고의 코드 블록을 고치면 parity 시험이 걸린다 — 둘을 같이 고친다.

## 기록 자리
`LOG.md` (이 폴더). 왜 그렇게 했는지 · 무엇이 틀렸었는지 · 실측 수치와 날짜.
