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

## minse 공공데이터 통합본

이 브랜치의 새 통합 앱은 루트 `apps/`에 있다. 기존 minse 앱 `ansimon-fullstack/`은 보존했다.
main의 앱 + 제공 공공데이터 134건 + KOSIS 통계 246행을 연결했다.
생활지원사 웹의 **공공데이터** 메뉴에서 지역 통계와 후보 검토 현황을 볼 수 있다.
원문 내용이 검토 기록과 일치하는 직접 생활지원 후보만 추천하고, 신청 자격·누락·사업별 확인일을 표시한다.

설치: 저장소 밖 Python 가상환경에서 `pip install -r apps/api/requirements.txt`, 각 `apps/web`·`apps/app`에서 `npm ci`.
실행·검사: 위 `scripts/dev-up.sh` / `scripts/test-all.sh`를 사용한다.
데이터 갱신·검토 방법과 한계는 [공공데이터 적용 문서](docs/공공데이터-적용.md)를 참고한다.
이 통합은 F11 공공데이터 문제를 다룬다. 인증·푸시·실제 전화망 등 원래 main 시제품의 운영 범위는 확대하지 않았다.
