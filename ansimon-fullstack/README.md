# 안심온 ANSIMON — 실행 및 통합 테스트 안내

React + Vite + Tailwind CSS / FastAPI + SQLite로 만든 **로컬 웹 안부전화 체험 앱**입니다. OpenAI API 키와 유료 대화 API는 필요하지 않습니다. 대화는 규칙 기반이며 실제 전화번호 발신·자동 119 신고·의학적 진단을 수행하지 않습니다.

## 1. 설치 전 준비와 정확한 폴더 열기

Windows 10/11, VS Code, Python 3.10 이상(3.12 권장), Node.js 22.12 이상 또는 24 LTS, Chrome/Edge를 준비하세요. 설치 후 VS Code를 완전히 닫았다가 다시 여세요. 검증 환경은 Linux / Python 3.12.14 / Node.js 24.22.1입니다. Windows에서 직접 실행한 결과라고 주장하지 않습니다.

1. GitHub 저장소의 브랜치를 **minse**로 선택하세요. [minse ZIP 다운로드](https://github.com/ptw786/2kimWon/archive/refs/heads/minse.zip)도 사용할 수 있습니다.
2. ZIP은 먼저 압축을 풉니다. 압축 파일 안에서 바로 실행하지 마세요.
3. VS Code에서 **파일 → 폴더 열기**로 `2kimWon-minse\ansimon-fullstack`을 여세요. 최상위 `2kimWon-minse`가 아니라 그 안의 `ansimon-fullstack`이 앱 폴더입니다.
4. **터미널 → 새 터미널**을 열고 셸이 PowerShell인지 확인하세요.
5. 아래 명령으로 현재 위치를 확인하세요. 마지막 두 줄이 모두 `True`여야 합니다.

```powershell
Get-Location
Test-Path .\backend\main.py
Test-Path .\frontend\package.json
```

설치된 프로그램 확인:

```powershell
py --version
node --version
npm.cmd --version
```

`py`가 없다면 Python 설치 시 launcher/PATH 옵션을 확인하거나 `python --version`을 확인한 후 아래의 `py` 명령만 `python`으로 바꿔 실행하세요. `npm.cmd`는 Node.js에 포함된 Windows 명령입니다. PowerShell의 `npm.ps1` 실행 정책 오류를 피하기 위해 사용하며, 전역 실행 정책을 바꿀 필요가 없습니다.

## 2. 백엔드 설치·실행 — 터미널 1

**현재 위치가 ansimon-fullstack인 상태**에서 실행합니다.

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

`Application startup complete`가 나오면 정상입니다. 서버가 실행되는 동안 터미널에 새 입력 프롬프트가 나오지 않는 것은 정상입니다. 터미널을 계속 열어 두세요. 종료할 때는 **Ctrl+C**입니다.

가상환경을 별도로 Activate하지 않고 해당 Python을 직접 실행하므로 `Activate.ps1` 권한 오류를 피할 수 있습니다. 이미 `.venv`가 있으면 생성 명령은 생략하고 의존성 설치부터 실행해도 됩니다. SQLite는 Python 기본 라이브러리이므로 따로 설치하지 않습니다.

- API 상태: http://127.0.0.1:8000/api/health
- API 문서: http://127.0.0.1:8000/docs
- 정상 상태 응답: `{"ok":true,"mode":"local-rule-based"}`
- health는 서버 프로세스뿐 아니라 실제 DB 연결과 필요한 테이블·열을 검사합니다. 준비되지 않으면 503과 원인 확인 안내를 반환합니다.

기본 DB는 실행 위치와 무관하게 **backend/ansimon.db**입니다. `ANSIMON_DB` 환경 변수가 있으면 그 경로를 사용하므로 기존 설정을 확인하세요. 사용자 지정 DB는 절대 경로 사용을 권장합니다. 기존 파일을 삭제하거나 새 DB로 바꿔 오류를 숨기지 마세요.

새 빈 DB의 최초 초기화에는 원래 프로젝트의 가상 어르신 4명이 들어갑니다. 기존 DB가 있으면 시작 전에 `ansimon.db.backup-<UTC시각>`으로 SQLite 스냅샷을 만들고 필요한 스키마만 추가합니다. 기존 통화·답변을 삭제하지 않습니다.

## 3. 프론트엔드 설치·실행 — 터미널 2

VS Code의 **터미널 → 새 터미널**로 별도 PowerShell을 엽니다. 현재 위치가 다시 **ansimon-fullstack**인지 확인하세요. 만약 backend 안이라면 `Set-Location ..`로 한 단계 올라온 뒤 실행하세요.

```powershell
Set-Location .\frontend
Test-Path .\package.json
npm.cmd ci
npm.cmd run dev
```

`npm ci`는 포함된 package-lock.json의 버전을 설치합니다. 첫 설치에는 인터넷이 필요합니다. `http://127.0.0.1:5173/`을 브라우저에서 여세요. 이 터미널도 계속 열어 둡니다.

- 관리 대시보드: http://127.0.0.1:5173/
- 어르신 전화 화면 예: http://127.0.0.1:5173/call/1
- 생활지원사 통화 기록: http://127.0.0.1:5173/records

프론트엔드는 같은 출처의 `/api/...`를 호출하고 Vite가 `http://127.0.0.1:8000`으로 전달합니다. DB는 프론트엔드나 브라우저 localStorage에 저장하지 않습니다. 5173 포트가 사용 중이면 다른 포트로 조용히 바꾸지 않고 실행 오류를 표시합니다.

## 4. 정상 실행을 확인하는 순서

1. 백엔드 health를 열어 `ok: true` 확인.
2. 대시보드의 날짜·관리 대상·어르신 목록 확인. 새 DB라면 가상 어르신 4명입니다.
3. 어르신 행의 **전화 체험** 클릭. 사이드바 없는 `/call/{id}` 화면으로 이동합니다.
4. 벨소리가 차단되면 **벨소리 켜기** 클릭. **전화 받기**를 누르면 벨소리가 멈추고 질문이 표시됩니다.
5. 음성이 없으면 텍스트로 답변하세요. 아래 다섯 답변은 각 질문에 맞춰 한 개씩 입력합니다.
   - 건강: `안 아파`
   - 식사: `밥 먹었어`
   - 수면: `잘 잤어`
   - 복약: `먹는 약 없어`
   - 기분: `기분 좋아`
6. **보내기** 또는 Enter로 제출합니다. 한국어 글자 조합 중 Enter는 제출하지 않습니다. 후속 응답을 읽은 뒤 다음 질문으로 이동합니다.
7. 다섯 문항이 확정되면 종료 인사 후 **안부 확인 완료**를 표시합니다. 이해하지 못한 답변에는 최대 두 번 재질문합니다.
8. **통화 기록**에서 완료 기록과 **보기** 상세를 확인하고 새로고침해도 같은 기록이 유지되는지 확인하세요.
9. 별도 체험에서 거절하면 **수신 거절**, 중간에 종료하면 **통화 중단** 기록이 남습니다.

마이크 버튼은 **마이크 시작/중지**입니다. 권한 거부·미지원·무음·인식 실패 시 텍스트로 전체 대화를 완료할 수 있습니다. ‘음성 끄기’로 현재 TTS를 중단할 수도 있습니다. 실제 발화 인식·음성 출력은 OS 음성, 마이크, 브라우저 정책과 네트워크에 따라 달라집니다.

## 5. 통화 기록과 DB 확인

통화 시작 때 calls 행, 매 답변 때 시도·확정 답변, 종료 때 상태·시각·요약을 저장합니다. 종료 전에도 ‘통화 중’ 기록을 조회할 수 있습니다. 별도의 ‘기록 저장’ 버튼은 필요하지 않습니다.

브라우저에서 다음 주소를 확인할 수 있습니다.

- http://127.0.0.1:8000/api/residents
- http://127.0.0.1:8000/api/calls
- http://127.0.0.1:8000/api/calls/1 — 실제 생성된 통화 ID로 바꾸세요.

PowerShell에서도 읽기 전용으로 확인할 수 있습니다.

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/health | ConvertTo-Json
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/calls | ConvertTo-Json -Depth 10
```

기록이 안 보이면 먼저 API 응답과 `ANSIMON_DB` 설정을 확인하세요. UI의 목록은 기본 최근 100건이며 API 최대 500건 제한을 유지합니다. 기존 데이터가 있는 다른 DB를 사용하던 경우 새 폴더의 빈 DB를 보고 있을 수 있습니다. 원래 DB와 백업을 지우지 말고 해당 경로를 확인하세요.

## 6. HTTP 500·저장 실패 해결

| 표시/증상 | 확인 및 조치 |
|---|---|
| 500 | 서버 내부 오류입니다. 화면의 API 경로·시각·상태코드와 터미널 1의 실제 예외를 확인하세요. 가짜 데이터로 성공 처리하지 않습니다. |
| health 503 | DB 파일이 없거나 연결·테이블/열 검사가 실패했습니다. DB 경로, 파일 권한, 초기화 로그를 확인하세요. health가 정상이라고 거짓 응답하지 않습니다. |
| 502 / FastAPI에 연결할 수 없음 | 터미널 1 서버가 127.0.0.1:8000에서 실행 중인지 확인하고 서버 복구 후 **다시 시도**하세요. |
| 요청 시간 초과 | 요청 또는 응답 본문이 15초 안에 끝나지 않았습니다. 답변을 그대로 두고 재시도하세요. 이미 저장됐다면 같은 순번으로 기존 결과를 반환합니다. |
| 422 | 빈 답변·길이·요청 형식 또는 질문 미완료 상태의 완료 요청입니다. `/docs`의 요청 형식과 화면 안내를 확인하세요. |
| 409 | 진행 중 통화나 다른 답변·순번의 충돌입니다. 동일 저장의 재전송은 안전하지만 다른 탭에서 먼저 진행했다면 같은 통화 화면에 재진입해 서버 상태를 불러오세요. |

이전의 시간대 DB 누락에 따른 대시보드 500은 한국 날짜를 UTC+09:00으로 계산하여 수정했습니다. 현재는 IANA 시간대 파일이나 별도 tzdata 설치 없이 처리합니다. 모든 500이 이 원인이라고 단정하지 말고 실제 서버 로그를 확인하세요.

DB가 잠겨 있으면 다른 DB 편집 도구를 닫고 잠시 후 재시도합니다. 파일에 쓰기 권한이 없으면 읽기 전용/압축 폴더가 아닌 쓰기 가능한 폴더에서 실행하세요. DB 파일 손상이 의심되면 서버를 멈추고 **DB와 기존 백업을 먼저 보존**한 뒤 점검해야 합니다. 이 문서는 DB 삭제·초기화를 해결 방법으로 안내하지 않습니다.

답변 저장 실패 시 현재 화면에 원문·순번이 유지됩니다. 저장 여부가 불확실한 답변은 편집을 잠그며 **다시 시도**로 같은 요청을 보냅니다. 새로고침/화면 이탈 전에는 아직 저장되지 않은 입력이 영구 보존되지 않는다는 점을 확인하세요. 저장된 통화는 같은 어르신 화면에 재진입하면 복원됩니다. 마지막 답변 뒤 종료 저장만 실패했다면 **완료 저장**을 누르세요.

## 7. 흔히 발생하는 설치·실행 오류

| 오류 | 해결 |
|---|---|
| py/python/npm을 찾을 수 없음 | Python/Node.js 설치 및 PATH를 확인하고 VS Code를 다시 시작하세요. |
| package.json 또는 requirements.txt 없음 | 잘못된 폴더입니다. `Get-Location`, `Get-ChildItem`으로 확인하고 frontend/backend에 각각 들어가세요. |
| npm.ps1 또는 Activate.ps1 실행 정책 오류 | `npm.cmd`와 `.\.venv\Scripts\python.exe`를 사용하세요. 가상환경 활성화나 실행 정책 변경은 필요하지 않습니다. |
| ModuleNotFoundError | 백엔드 가상환경의 Python으로 requirements 설치와 uvicorn 실행을 모두 했는지 확인하세요. |
| 포트 8000/5173 사용 중 | 이전에 실행한 서버 터미널에서 Ctrl+C를 누르세요. 다른 프로세스를 임의로 강제 종료하지 말고 어떤 프로그램인지 확인하세요. |
| CORS 오류 | 개발 UI를 127.0.0.1:5173 또는 localhost:5173에서 여세요. 백엔드는 이 두 출처만 허용합니다. API 500과 CORS를 구분하세요. |
| 마이크 권한 거부/미지원 | Chrome/Edge에서 localhost/HTTPS로 접속하고 주소창 마이크 권한을 확인하거나 텍스트로 답변하세요. |
| 한국어 TTS 음성 없음 | OS 한국어 음성과 브라우저 지원을 확인하세요. 앱의 텍스트 대체로 대화를 완료할 수 있습니다. |
| 벨소리가 안 남 | ‘벨소리 켜기’, 브라우저/OS 음량을 확인하세요. 수신·거절 자체는 무음에서도 가능합니다. |
| npm ci 설치 실패 | 설치 오류의 실제 메시지와 네트워크를 확인하세요. package-lock.json을 임의로 지우지 마세요. |
| 빌드는 되지만 정적 배포 API가 안 됨 | 이 안내는 Vite 개발 서버 기준입니다. 정적 배포에는 `/api` 백엔드 프록시와 SPA fallback이 별도로 필요합니다. |

## 8. 자동 테스트 실행

백엔드 테스트는 **backend 폴더**에서 실행합니다. 테스트는 별도 임시 DB를 쓰므로 현재 ansimon.db를 초기화하지 않습니다.

```powershell
.\.venv\Scripts\python.exe -m pytest -q .\tests
```

프론트엔드 테스트와 빌드는 **frontend 폴더**에서 실행합니다.

```powershell
npm.cmd test
npm.cmd run build
```

브라우저 통합 테스트는 먼저 두 개발 서버를 **Ctrl+C로 모두 종료**해야 합니다. 테스트가 직접 8000/5173 서버를 시작·종료합니다. 다른 서버가 있으면 데이터를 잘못 건드리지 않도록 실행을 거부합니다.

**ansimon-fullstack 프로젝트 루트**의 PowerShell에서 실행하세요.

```powershell
.\backend\.venv\Scripts\python.exe -m pip install playwright
.\backend\.venv\Scripts\python.exe -m playwright install chromium
.\backend\.venv\Scripts\python.exe .\frontend\tests\e2e.py
```

브라우저 테스트도 임시 DB를 사용합니다. 백엔드 Python은 backend/.venv를 우선 찾고 기존 루트 .venv도 지원합니다. 다른 Python을 쓰려면 `ANSIMON_PYTHON`에 경로를 지정할 수 있습니다. Linux의 기존 루트 가상환경 구성은 `.venv/bin/python -m pytest -q backend/tests`, `npm test`/`npm run build`(frontend), `python frontend/tests/e2e.py` 명령을 사용합니다.

최종 검증 결과와 실패 재현·수정 근거는 [최종 통합 테스트 보고서](docs/FINAL_INTEGRATION_REPORT.md)에 있습니다. 실제 마이크 인식과 한국어 음성 청감은 자동 이벤트 주입 테스트와 구분하며, 장치 없는 클라우드 환경에서는 미검증입니다.

## 9. 소스 폴더 구조

`.venv`, node_modules, 실제 DB·백업은 설치/실행 시 생성되며 저장소에는 포함하지 않습니다.

```text
ansimon-fullstack/
├── README.md
├── .gitignore
├── backend/
│   ├── main.py                      # FastAPI·DB 초기화/백업·저장·조회·readiness
│   ├── conversation.py              # 5문항·분류·후속 응답·원문 요약
│   ├── requirements.txt
│   └── tests/
│       ├── conftest.py              # 임시 DB fixture
│       ├── test_api.py
│       ├── test_regressions.py
│       ├── test_conversation.py
│       └── test_final_integration.py
├── frontend/
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js               # 5173 → 8000 /api 프록시
│   ├── index.html
│   ├── src/
│   │   ├── main.jsx
│   │   ├── App.jsx                  # /, /call/:elderId, /records
│   │   ├── api.js                   # 공통 API·15초 제한·오류 처리
│   │   ├── styles.css
│   │   ├── pages/
│   │   │   ├── DashboardPage.jsx
│   │   │   ├── CallPage.jsx
│   │   │   └── RecordsPage.jsx
│   │   ├── components/
│   │   │   ├── Sidebar.jsx
│   │   │   ├── Common.jsx
│   │   │   ├── Feedback.jsx
│   │   │   ├── IncomingCall.jsx
│   │   │   ├── ActiveCall.jsx
│   │   │   ├── CallControls.jsx
│   │   │   ├── ConversationPanel.jsx
│   │   │   ├── TextAnswerInput.jsx
│   │   │   └── SpeechInputStatus.jsx
│   │   ├── hooks/
│   │   │   ├── useCall.js
│   │   │   ├── useResource.js
│   │   │   └── useRingtone.js
│   │   └── speech/
│   │       ├── recognition.js
│   │       └── synthesis.js
│   └── tests/
│       ├── api.test.js
│       ├── speech.test.js
│       ├── e2e.py
│       ├── conversation_scenarios.py
│       ├── speech_input_scenarios.py
│       ├── final_scenarios.py
│       ├── audio_probe.js
│       └── speech_probe.js
└── docs/
    ├── FINAL_INTEGRATION_REPORT.md
    ├── conversation-flow.md
    ├── conversation-flow.svg
    ├── conversation-flow-storage.svg
    ├── CONVERSATION_ENGINE.md
    ├── SPEECH_INPUT_REPORT.md
    ├── ROUTING_RINGTONE_REPORT.md
    ├── REPAIR_REPORT.md
    ├── REFERENCES.md
    └── verification/                 # 검증 로그
```

## 10. API 주소와 데이터 형식

| 메서드·주소 | 요청/응답 |
|---|---|
| GET /api/health | 정상 `{ok,mode}` / DB 미준비 503 detail |
| GET /api/residents | `{id,name,age,neighborhood,call_time}` 배열 |
| GET /api/dashboard | 날짜·상태별 수·어르신 배열 |
| GET /api/questions | `{topic,text}` 5개 배열 |
| POST /api/residents/{id}/calls | 선택 Idempotency-Key, 201 `{id,resident_id,status,question,topic}` |
| POST /api/residents/{id}/decline | 선택 Idempotency-Key, 201 `{id,status}` |
| POST /api/calls/{id}/turns | `{answer,index,attempt}` → count/classification/reply/needs_retry/next_attempt/next_question/finished 등 |
| POST /api/calls/{id}/finish | `{status:"completed"}` 또는 `{status:"interrupted"}` → id/status/summary/answered |
| GET /api/calls | 목록. 선택 resident_id·limit |
| GET /api/calls/{id} | 통화 + turns/attempts/dialogue_state |

index는 0~4, attempt는 최초 0·재답변 1·2입니다. 같은 순번·같은 답변 재전송은 기존 결과를 반환합니다. 종료도 같은 상태 재전송을 허용합니다. API 오류는 화면에 경로·HTTP 코드 또는 연결/시간 초과 메시지로 표시합니다.

## 11. 구현 문서

- [실제 STT → 대화 → 저장 흐름도](docs/conversation-flow.md)
- [전체 흐름 SVG](docs/conversation-flow.svg) · [답변 저장 상세 SVG](docs/conversation-flow-storage.svg)
- [규칙 기반 대화 엔진](docs/CONVERSATION_ENGINE.md)
- [STT/TTS 구현·검증 범위](docs/SPEECH_INPUT_REPORT.md)
- [화면 분리·벨소리](docs/ROUTING_RINGTONE_REPORT.md)
- [초기 HTTP 500 수정](docs/REPAIR_REPORT.md)
- [참고 자료](docs/REFERENCES.md)

## 후속 출시 준비 체크

현재 구현과 분리된 후속 준비 항목입니다. 실제 전화 서비스·LLM·자동 119 신고는 현재 기능이 아닙니다.

1. 사용자 로그인·접근 권한·HTTPS·개인정보 보존/삭제 정책.
2. 실제 전화/문자 사업자 연동과 통화 동의·실패 관리.
3. 운영 DB·백업 운영·배포·접근성 및 실제 Windows/음성 장치 검증.
4. 여러 탭에서 다른 답변을 보낸 409 충돌의 사용자 안내·동기화 개선, 미저장 초안의 새로고침 보존, 기록 페이지네이션.
