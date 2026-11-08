# 안심온 (ANSIMON) — React + FastAPI + SQLite

**실제 프론트엔드와 백엔드로 동작하는 로컬 개발 앱**입니다. OpenAI API 키 불필요. 기존 단일 HTML 버전에서 구조를 바꿨습니다.

> ⚠️ 이 프로젝트는 **로컬 개발·검증용**입니다. 실제 전화번호 발신이 아닌 웹 통화입니다. 공개 서비스로 배포하거나 실제 어르신 개인정보를 넣기 전에 반드시 사용자 인증·접근권한·HTTPS·개인정보 처리 동의·보존/삭제 정책·보안 감사 및 음성 인식 전송 고지를 구현해야 합니다. 의료 판단 또는 긴급 구조 시스템으로 사용하지 마세요.

## 설치 전 준비

- Windows 10/11 + VS Code
- [Python](https://www.python.org/downloads/) 3.10 이상 (설치 시 **Add Python to PATH** 체크)
- [Node.js](https://nodejs.org/) 20.19 이상 또는 22.12 이상 (권장 최신 LTS)
- Chrome 또는 Edge. 음성 기능은 브라우저·OS·권한·네트워크에 따라 제한될 수 있음

## 1. VS Code에서 폴더 열기

ZIP 압축 해제 → `ansimon-fullstack` 폴더를 VS Code에서 `파일 > 폴더 열기`로 열어주세요. **VS Code 메뉴 `터미널 > 새 터미널`** 클릭. 터미널 두 개를 엽니다.

## 2. 백엔드 실행 (터미널 1 — PowerShell)

```powershell
cd backend
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Python 실행 파일이 `py`가 아니라 `python`이면 `python -m venv .venv`를 사용하세요.

- 테스트 페이지: http://127.0.0.1:8000/docs
- API 건강 상태: http://127.0.0.1:8000/api/health
- 첫 실행 시 `backend/ansimon.db`에 가상 어르신 4명이 저장됩니다.

## 3. 프론트엔드 실행 (터미널 2 — PowerShell)

```powershell
cd frontend
npm install
npm run dev
```

브라우저에서 **http://127.0.0.1:5173** 열기. 파일을 더블클릭해 `file:///.../index.html`로 여는 방식은 사용하지 않습니다.

## 4. 앱 사용 방법

1. **대시보드**에서 관리 대상/안부 확인 상태 및 어르신 목록 확인.
2. 어르신 행의 **전화 체험** 클릭 → 어르신 전용 전화 화면으로 이동.
3. **전화 받기** 클릭 → 음성 질문 출력 → **말하기** 버튼으로 답변(Chrome/Edge 마이크 허용) 또는 입력창 답변.
4. 다섯 질문에 답하면 **안부 확인 완료**. 중간에 끊으면 **통화 중단**, 수신을 거절하면 **수신 거절**.
5. **통화 기록**에서 날짜/결과/요약/실제 답변 확인. 새로고침해도 SQLite에 남습니다.

음성 인식이 되지 않아도 입력창과 빠른 답변 버튼으로 앱 전체 흐름을 확인할 수 있습니다.

## 주요 폴더

```
ansimon-fullstack/
├── frontend/
│   ├── package.json         # React/Tailwind/Vite 의존성
│   ├── vite.config.js        # 개발 서버 /api 프록시
│   ├── index.html            # React 진입 HTML
│   └── src/
│       ├── main.jsx          # React 실행
│       ├── App.jsx           # 대시보드, 기록, 전화 페이지
│       ├── api.js            # 서버 API 호출
│       └── styles.css        # Tailwind + 사용자 정의 UI
├── backend/
│   ├── requirements.txt      # FastAPI 등 Python 라이브러리
│   ├── main.py               # API / SQLite 모델 / 규칙 기반 응답
│   └── tests/test_api.py     # API 테스트
├── docs/REFERENCES.md       # GitHub 오픈소스 3개 조사
└── .gitignore
```

## API 목록

| Method | URL | 역할 |
|---|---|---|
| GET | `/api/health` | 서버 상태 |
| GET | `/api/residents` | 어르신 목록 |
| GET | `/api/dashboard` | 오늘 안부 확인 상태 |
| GET | `/api/questions` | 5개 질문 |
| POST | `/api/residents/{id}/calls` | 통화 시작 |
| POST | `/api/residents/{id}/decline` | 수신 거절 기록 |
| POST | `/api/calls/{id}/turns` | 답변 저장 + 다음 질문 |
| POST | `/api/calls/{id}/finish` | 완료 또는 중단 |
| GET | `/api/calls` | 통화 목록 |
| GET | `/api/calls/{id}` | 전체 질문·답변 |

API 문서에 요청/응답 JSON 예시를 볼 수 있습니다: `/docs`.

## 테스트

```powershell
cd backend
.venv\Scripts\python.exe -m pytest -q
```

프론트엔드 빌드:

```powershell
cd frontend
npm run build
```

## 흔한 오류

- **`npm`을 찾을 수 없음:** Node.js 설치 후 VS Code 완전히 껐다 다시 켜기. `node -v`, `npm -v` 확인.
- **`py` 명령 없음:** `python -m venv .venv` 사용. Python PATH 확인.
- **`Failed to fetch`/백엔드 연결 불가:** `uvicorn` 터미널이 켜져 있는지, 8000번 포트인지 확인.
- **`Address already in use`:** 이미 8000번 포트의 서버가 켜져 있을 수 있음. 중복 실행 중지.
- **마이크 권한 오류:** Chrome/Edge에서 `127.0.0.1`으로 접속, 주소창 권한에서 마이크 허용. Chrome Web Speech 구현은 외부 서버를 이용할 수 있음.
- **통화 중 새로고침:** 같은 어르신의 전화 체험 화면을 다시 열면 진행 중 통화와 저장된 답변을 불러옵니다. 마지막 답변 뒤 종료 저장에 실패했다면 **완료 저장** 버튼으로 재시도하세요. DB를 삭제할 필요가 없습니다.
- **대시보드 500:** 한국 날짜는 UTC+09:00으로 계산하므로 Windows의 IANA 시간대 DB 설치 여부와 무관합니다. 계속 실패하면 화면의 API 경로·상태코드와 백엔드 로그를 확인하세요.
- **DB 보존:** 기존 DB가 있으면 백엔드 시작 시 `ansimon.db.backup-<UTC시각>`으로 SQLite 스냅샷을 만든 뒤 필요한 열·인덱스만 추가합니다. `ANSIMON_DB`로 다른 DB 경로를 지정할 수 있습니다. 기존 파일과 백업을 지우지 마세요.
- **Tailwind 설치 오류:** 네트워크 연결 확인 후 `npm install` 재실행.

## GitHub 업로드

루트 폴더에서 아래 명령을 실행. 개인 데이터와 `.venv`, `node_modules`, `.db` 파일은 `.gitignore`에서 제외합니다.

```bash
git init
git add .
git commit -m "Build ANSIMON full-stack web app"
git branch -M main
git remote add origin https://github.com/본인계정/본인저장소.git
git push -u origin main
```

이미 저장소가 있다면 기존 README/파일과 충돌할 수 있으므로 먼저 백업하거나 새 브랜치에 올리세요.

## 구현 범위 / 기술 설명

- **React + Vite + Tailwind CSS**: 어르신 전화 화면과 생활지원사 관리 화면 분리.
- **Web Speech API / SpeechSynthesis**: 브라우저 한국어 음성 인식과 질문 낭독. 음성 인식은 브라우저가 외부 처리할 수 있어 완전한 오프라인은 아님.
- **FastAPI**: 전화 시작·거절·답변·종료를 REST로 처리. 질문 순서 및 간단한 후속 응답을 규칙으로 결정.
- **SQLite**: `residents`, `calls`, `turns` 3개 테이블에 저장. 브라우저 새로고침 후에도 유지.
- **실제 생성형 AI 아님**: AI라고 표시된 통화는 미리 정한 규칙 기반 대화이며, 별도의 자연어 모델/실제 통신망은 아직 없음.
- **현재 보안 한계**: 인증·권한·서버 보안/암호화/기록 삭제 기능이 없어 실제 사용자를 대상으로 서비스할 수 없음.

## 후속 출시 준비 체크

1. 사용자 로그인과 생활지원사별 데이터 접근 권한, 감사 로그 및 개인정보 보호 규정 확립.
2. 실제 전화 발신 및 문자/전화 사업자 연동(대체로 비용 발생), 통화 동의와 통화 실패 관리.
3. 운영 환경 DB, 백업, 삭제·보존 정책, 앱 배포 자동화, 사용자/장애인 접근성 테스트.
4. 사회보장 공개 데이터 출처·이용 조건을 확인하고 통계 기반 지역 필요도 분석과 제품 기능의 연관성 검증.

참고한 프로젝트별 링크/라이선스/적용 내용은 `docs/REFERENCES.md`를 확인하세요.

### 오류 수정 검증 (2026-11-09, 한국 시간)

- API 자동 테스트 8개 통과: 전체 통화 흐름, 시간대 DB 없는 환경, 동시·재전송 중복 방지, DB 백업·기존 스키마 보존, 별도 프로세스 재실행, CORS, DB 오류 메시지.
- React/Vite 프로덕션 빌드 통과. `package-lock.json`을 포함하므로 이후 `npm ci`를 사용할 수 있습니다.
- 실제 Uvicorn + Vite + Chromium 자동 검증 통과: 중단된 백엔드 오류 표시, 다시 시도 재호출, 목록, 5문항 통화, 진행 중 새로고침 복원, 종료 응답 유실 후 재시도, 기록 조회, 새로고침·백엔드 재시작 후 보존.
- 상세 결과와 원인, 변경 파일: [docs/REPAIR_REPORT.md](docs/REPAIR_REPORT.md).

선택적 브라우저 자동 테스트(8000/5173 포트에 실행 중인 서버가 없어야 함):

```powershell
# 프로젝트 루트에서, backend/.venv를 사용하는 Windows 예시
backend\.venv\Scripts\python.exe -m pip install playwright
backend\.venv\Scripts\python.exe -m playwright install chromium
$env:ANSIMON_PYTHON = (Resolve-Path backend\.venv\Scripts\python.exe).Path
backend\.venv\Scripts\python.exe frontend/tests/e2e.py
```

테스트는 임시 DB를 사용합니다. Linux에서 루트 `.venv`를 만든 경우 `python frontend/tests/e2e.py`로 실행할 수 있으며, 다른 Python 경로는 `ANSIMON_PYTHON`에 지정하세요. 브라우저 테스트에는 별도의 Playwright 설치가 필요합니다. 마이크·한국어 음성 출력은 실제 OS·권한 환경에서 별도 확인해야 합니다.
