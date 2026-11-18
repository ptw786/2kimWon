# 2kimWon — 안심온 (ANSIMON)

> 2026 사회보장 데이터를 활용한 AI 혁신 아이디어 경진대회 · DatAIve 2팀 (민세 · 예인 · 태원)

독거 어르신에게 정해진 시간에 AI가 안부전화를 걸고, 답변을 근거와 함께 정리해 생활지원사가 **오늘 먼저 챙길 분**을 볼 수 있게 하는 서비스.

```
apps/api   서버 (FastAPI · SQLite · Ollama)   :8010
apps/web   소개 + 생활지원사 웹                 :5180
apps/app   어르신 앱 (PWA)                      :5181
```

- 처음이라면: [`docs/harness/README.md`](docs/harness/README.md) → [`docs/harness/기능-명세.md`](docs/harness/기능-명세.md)
- 실행: `scripts/dev-up.sh` (WSL) · 각 앱 README에 Windows PowerShell 명령
- 검사: `scripts/test-all.sh`
- 이전 버전: `minse` 브랜치의 `ansimon-fullstack/` (참고용)

이 저장소의 어르신·통화 데이터는 모두 가상입니다. 의료 판단이나 119 자동 신고를 하지 않습니다.

## main 공공데이터 통합 (2026-11-18)

최신 main의 PIN 로그인·안전 알림·규칙 r3·진주빛 배경을 유지하고 제공 공공데이터를 통합했다.
루트 `apps/api`, `apps/web`, `apps/app`을 실행한다. 생활지원사 웹의 **공공데이터** 메뉴에서 지역 통계와 검토 현황을 볼 수 있다.
신규·내용 변경 사업은 재검토 전까지 추천하지 않고, 신청 조건·누락·사업별 정보 확인일을 표시한다.

자세한 변경·해결 내용과 남은 한계: [공공데이터 적용](docs/공공데이터-적용.md).
검증: [main 통합 검증](docs/평가/2026-11-18_main_public_data.md).
