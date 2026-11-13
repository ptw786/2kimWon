# 안심온 (ANSIMON) — 작업 규약 요약

독거 어르신 AI 안부전화. 서버 `apps/api` 하나를 생활지원사 웹 `apps/web`과 어르신 앱 `apps/app`이 같이 쓴다.
코드 작업 전에 읽을 것:

- 구조와 모듈 책임: `docs/harness/README.md`
- 기능 ID·담당·코드 위치: `docs/harness/기능-명세.md` (F0~F11)
- 코딩 규약: `docs/harness/코딩-규약.md`
- 계획과 결정 대기 항목: `docs/harness/구현-계획.md`
- 사람·AI 역할: `docs/harness/AI-개발-분배.md`, 역할 에이전트 `.claude/agents/`
- 판정 규칙: `docs/판정규칙.md` (값은 `apps/api/app/domain/rules.yaml`)
- 디자인: `docs/디자인.md`, 시안 `packages/design/preview-v3.html`, 토큰 `packages/design/tokens.css`
- API 약속: `packages/contracts/CONTRACT.md`
- 결정 기록: `docs/adr/`

## 꼭 지킬 것

1. `apps/api/app/domain/`은 순수 함수만. 판정규칙 표 한 줄 = 함수 하나 = 테스트 하나. 값은 `rules.yaml`에만.
2. 외부 호출(Ollama, 복지서비스 데이터)은 `apps/api/app/services/` 어댑터로만. LLM은 DB 쓰기 트랜잭션 밖에서.
3. 안전 신호는 규칙으로만 판단한다. AI는 확인 대상을 늘리는 쪽으로만 쓴다. 나이·성별은 점수에 넣지 않는다. 진단이 아니다.
4. AI 결과는 어르신 답변 안에 인용이 있을 때만 쓴다. 실패하면 규칙으로 대체하고 `ai_runs`에 남긴다.
5. API 모양을 바꾸면 `CONTRACT.md` → 서버 → 웹 → 앱을 같은 작업에서 고친다.
6. 화면: `tokens.css` 변수만, **왼쪽 색 선 금지**, 글자 웹 16px·앱 20px 이상, 상태는 아이콘+한글 라벨. 디자인은 사용자의 이전 작업(디자인.md 출처표)을 직접 보고 따른다.
7. 웹·앱은 서로 import하지 않는다. 각 앱은 `src/app · features · shared · mock` 틀을 쓴다.
8. 완료라고 하려면 증거: `scripts/test-all.sh` 결과, 화면은 스크린샷, 통합은 "웹에서 걸기 → 앱 벨 → 5문항 → 웹 반영" 1회.
9. 이전 버전(팀원 통합본)은 `minse` 브랜치의 `ansimon-fullstack/`에 있다 — 수정하지 않는다. 가상 환경을 저장소 안에 만들지 않는다(Windows 폴더). 커밋·푸시는 사람이 정한다.

## 실행

```bash
scripts/dev-up.sh     # api :8010 · web :5180 · app :5181 (WSL)
scripts/test-all.sh   # pytest · web build · app build+test
```
