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
