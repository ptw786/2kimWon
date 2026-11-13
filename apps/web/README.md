# 안심온 웹 (생활지원사 화면)

React 19 + Vite + TypeScript. 시안은 `packages/design/preview-v3.html`의 ①~④, 색·글꼴 값은 `packages/design/tokens.css`를 그대로 가져다 써요. API 모양은 `packages/contracts/CONTRACT.md`를 따라요.

## 실행

API(`apps/api`, 127.0.0.1:8010)를 먼저 켜 두면 실제 데이터로 보여요. API 없이 화면만 보려면 목업 모드를 쓰세요.

### Windows PowerShell

```powershell
cd apps\web
npm install            # 처음 한 번 (WSL에서 설치한 node_modules가 있으면 지우고 다시 설치)
npm run dev            # http://localhost:5180  (실제 API로 /api 연결)
npm run dev:mock       # 가짜 데이터로 실행 (API 필요 없음)
npm run build          # 타입 검사 + 배포용 빌드 (dist/)

# 폰에서 QR로 어르신 앱을 열려면, 같은 와이파이의 PC 주소를 넣고 실행
$env:VITE_APP_PUBLIC_URL = "http://192.168.0.12:5181"; npm run dev
```

### WSL (bash)

```bash
cd apps/web
npm install
npm run dev            # /mnt/c 아래에서는 파일 변경을 폴링으로 감시해요(vite.config.ts)
npm run dev:mock
npm run build
VITE_APP_PUBLIC_URL=http://192.168.0.12:5181 npm run dev
```

> node_modules에는 운영체제별 실행 파일(esbuild·rollup)이 들어 있어서, Windows와 WSL을 오가면 그쪽에서 `npm install`을 다시 해야 해요.

### 화면 검사 (선택)

```bash
npm run dev:mock &                 # 5180에서 목업 서버
python3 scripts/shots.py           # 모든 화면 1440·1024·390 스크린샷 + 가로 스크롤·16px 미만 글자 검사 → screenshots/
python3 scripts/flows.py           # KPI 필터·확인 기록·전화 걸기·어르신 추가·다크 모드·데모 리셋 동작 확인
```

## 화면

| 주소 | 화면 | 쓰는 API |
|---|---|---|
| `/` | 소개 — 히어로, 1→4 흐름, QR(KY-01), 오른쪽 폰 안에 **실제 어르신 앱**(iframe). 앱이 꺼져 있으면 벨 화면 예시 | – |
| `/staff` | 오늘 확인 순서 — KPI(눌러서 거르기), 확인 순서 카드(첫 분 ★), 오른쪽 상세(3박스·7일 표), 5초마다 새로고침 | `GET /staff/dashboard`, `GET /staff/residents/{id}`, `POST /staff/residents/{id}/call`, `POST /staff/calls/{id}/check` |
| `/staff/live` | 실시간 통화 — 큰 QR·코드, 시연 도구(전화 걸기), 대화 레인 2초마다, 새 말은 버터색 링 | `GET /staff/live`, `GET /staff/calls/{id}` |
| `/staff/calls` | 통화 기록 — 날짜·단계로 거르기 | `GET /staff/calls?date=` |
| `/staff/calls/:id` | 통화 상세 — 오늘 통화 목록 · 질문별 세로 타임라인 · 점수 구성·AI 실행 기록·확인 기록 | `GET /staff/calls/{id}`, `POST /staff/calls/{id}/check` |
| `/staff/residents` | 어르신 목록 + 추가·수정 | `POST/PATCH /staff/residents` |
| `/staff/rules` | 판정 기준 (docs/판정규칙.md를 표로) | – |
| `/staff/principles` | 데이터 원칙 | – |

공통: 사이드바 아래 AI 상태(`GET /health`), 위쪽 ‘가상 데이터’·AI 상태 칩, 데모 리셋(`POST /staff/demo/reset`, 확인 창), 다크 모드. API가 꺼져 있으면 빨간 띠로 알려요.

## 환경 변수

| 이름 | 기본값 | 뜻 |
|---|---|---|
| `VITE_APP_PUBLIC_URL` | `http://<지금 연 주소의 호스트>:5181` | 어르신 앱 주소. QR(`…/r/KY-01`)과 소개 페이지 iframe에 써요. 폰으로 찍으려면 PC의 와이파이 주소로 |
| `VITE_MOCK` | (없음) | `1`이면 `src/mock`의 가짜 서버가 응답해요. `npm run dev:mock`이 `.env.mock`으로 켜요 |

`/api`는 개발 서버가 `http://127.0.0.1:8010`으로 넘겨요(vite.config.ts). 포트 5180은 `strictPort`라 이미 쓰이고 있으면 켜지지 않아요.

## 파일

- `src/shared/status.ts` — 단계·항목·통화 상태의 한글 라벨과 아이콘(여기 하나에서만 정함)
- `src/shared/types.ts` — CONTRACT.md 타입
- `src/shared/api.ts` — `/api` 호출, 서버 연결 상태(배너), 목업 전환
- `src/mock/` — 목업 데이터(시안 예시: 박정호 긴급, 김영자 오늘 확인 …)와 메모리 속 가짜 서버
- `src/strings/rules.ts` — 판정 기준 화면 문구
- `src/styles/app.css` — 화면 스타일(토큰만 사용, 다크 모드 덮어쓰기 포함)

## 아직 가짜인 부분

- **목업 모드 전체**: 새로고침하면 처음 상태로 돌아가요. 목업의 ‘실시간 통화’는 정해진 대본이 5초마다 한 턴씩 늘어나는 흉내예요(실제 앱·음성과 연결되지 않음).
- **어르신·통화 데이터**: 실제 API에서도 시드된 가상 인물이에요.
- **‘남은 분께 일괄 전화’**: 전용 API가 없어서, 아직 통화 전인 분마다 `POST /staff/residents/{id}/call`을 차례로 불러요.
- **시안의 ‘가상 통화 3건 보내기’ 버튼**: 계약에 해당 API가 없어 넣지 않았어요.
- **소개 페이지 폰**: 어르신 앱(5181)이 꺼져 있으면 움직이지 않는 벨 화면 예시를 보여 줘요.
- **로그인·권한**: 없어요. 생활지원사 한 명이 쓰는 시연용이에요.
