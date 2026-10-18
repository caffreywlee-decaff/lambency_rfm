# lambency_rfm LOG

## 2026-10-18 — v0.1.0 만듦
- 계기: 블로그 20편 v6 가 RFM 코드 스무 줄을 공개 → 카프 «누구나 카피해서 쓸 수 있는 MCP 로 … 무게·블렌드·세그먼트 수 바꿀 수 있게» → «풀어도 되고 lambency_rfm 으로».
- 꼴은 bytemescan 과 같다(MIT · MCP+CLI · README 한/영 · 순수 로직 시험). 이름 충돌: PyPI lambency-rfm/lambency_rfm/lambency 없음(404), GitHub caffreywlee-decaff/lambency_rfm 없음, GitHub 검색 0 (2026-10-18 실측).
- 설계: 계산은 core.py 한 곳. 규칙 우선순위 큰손 > 잠든 > 신규 > 구간표(글 12 와 같음). 구간표 이름을 바꾸면 모양 묶음은 순서 3등분 + 출력에 note.
- 글의 코드와 같은 등급을 내는지 `tests/test_article_parity.py` 가 합성 2,000명으로 확인(글이 있는 환경에서만).
- 2026-10-18 server 임포트 fallback 시험 추가(`tests/test_server_import.py`): 가짜 mcp 모듈로 1.x · 2.x · 둘 다(1.x 우선) · 없음(SystemExit + pip 안내) 네 경우. byteme 세션이 bytemescan 에 같은 꼴로 넣은 걸 따름. 실제 mcp 2.3.0 에서도 MCPServer 로 뜸.
