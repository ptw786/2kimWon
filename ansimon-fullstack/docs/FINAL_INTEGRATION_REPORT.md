# 최종 통합 테스트 결과

검증일: 2026-11-09 (한국 시간). GitHub minse의 앱/문서 커밋 `983ed4b`를 기준으로 테스트하고 발견한 결함을 수정했다. main 브랜치와 프로젝트 밖의 파일은 작업 대상이 아니다.

## 1. 결론

**수정 후 pytest 76개, 프론트엔드 자동 테스트 34개, 실제 서버·Chromium 시나리오 29개 묶음, React 빌드가 통과했다.** 정상 흐름의 예상하지 않은 HTTP 500은 0건이다. 의도적으로 주입한 500 4건은 별도로 식별했고, 실제 서버 중단/복구·저장 응답 유실·응답 본문 시간 초과를 검증했다.

최종 통합 테스트 임시 DB를 읽기 전용으로 직접 검사했다. **18개 통화(완료 7·거절 1·중단 10), 확정 답변 42개, 전체 답변 시도 44개**가 있었다. 재질문 때문에 시도 수가 확정 답변 수보다 많다. 모든 완료 통화에 5개 답변과 요약·종료 시각이 있고 거절/중단 상태도 일치했다. 중복 답변·중복 시도·외래 키 위반·남은 in_progress는 모두 0이다. SQLite integrity_check는 ok다.

이 결과는 검증한 스키마·테스트 데이터·환경에 대한 결과이며, 모든 환경에서 오류가 불가능하다는 의미는 아니다. 실제 사용자 PC의 DB나 Windows 실행·마이크 인식 성공까지 확인했다고 주장하지 않는다.

## 2. 발견한 결함과 수정 전 실패

기존 테스트는 먼저 **70 API / 28 프론트엔드 / 25 브라우저 / 빌드 통과**를 재확인했다. 추가 장애 테스트에서 다음 결함을 재현했다.

| 결함 | 수정 전 관측 | 수정 |
|---|---|---|
| health가 DB 미준비를 정상으로 오인 | DB 경로를 별도 누락 파일/초기화 안 된 임시 DB로 지정해도 health 200·ok true. 새 검사 2개 실패 | 실제 파일·DB 연결·필요한 테이블/열을 검사. 미준비면 503 detail. health는 DB를 새로 만들거나 초기화해 오류를 숨기지 않음 |
| API 응답에 제한 시간이 없음 | fetch 또는 JSON 본문이 끝나지 않을 때 설정한 제한 시간을 넘겨 계속 pending. 새 검사 2개 실패 | 요청 시작부터 JSON 해석까지 기본 15초 AbortController 제한. 화면 이동 취소와 시간 초과를 구분. 원문·순번과 기존 저장 로직을 유지하여 안전하게 재시도 |

수정 전의 **실패 4개는 실제 로그에 남겼고 수정 후 모두 통과**했다. 이를 정상 통과로 바꾸어 보고하지 않는다. health 결함은 DB 장애를 감추던 상태 확인 오류이며, 사용자 PC의 과거 500 원인이라고 단정하지 않는다. 기존 시간대 DB 누락 500 수정은 PYTHONTZPATH 없는 환경의 회귀 테스트로 재확인했다.

실제 서버가 답변을 저장한 뒤 클라이언트의 응답 본문만 멈추게 한 테스트에서는 DB에 이미 1행이 있어도 UI는 아직 답변을 확정하지 않았다. 15초 후 원문을 보존하고 ‘다시 시도’로 기존 결과를 받아 **추가 행 없이** 다음 질문으로 이동했다. 이 경우를 단순히 저장 실패로 단정하지 않고 ‘저장 여부를 확인하지 못함’으로 안내한다.

## 3. 필수 테스트 20개

| 번호 | 항목 | 결과 | 확인 근거 |
|---|---|---|---|
| 1 | FastAPI 실행 | 통과 | 실제 Uvicorn 실행·health 200 및 DB 준비 검사 |
| 2 | React 실행 | 통과 | 실제 Vite 5173 HTTP·React 페이지 렌더 |
| 3 | 대시보드 | 통과 | 현황·날짜·통계·오류 재시도 |
| 4 | 어르신 목록 | 통과 | 실제 residents API 및 4개 초기 샘플 행 |
| 5 | 전화 수신 화면 | 통과 | /call/:elderId 라우팅·직접 접근 |
| 6 | 벨소리 시작/종료 | 자동 검증 통과·청감 미검증 | native Web Audio 노드 실행·중단·close, 청감은 미검증 |
| 7 | 전화 수신 | 통과 | 실제 start API·진행 중 통화 ID, 연속 클릭 단일 저장 |
| 8 | TTS 질문 | 자동 검증 통과·청감 미검증 | 한국어 TTS 호출·순서·완료 이벤트 주입 검증, 실제 한국어 청감 미검증 |
| 9 | 텍스트 제출 | 통과 | 버튼·Enter·IME·빈 입력·중복 방지·저장 |
| 10 | 답변 판정 | 통과 | 질문별 분류·후속 응답 및 API/DB 일치 |
| 11 | 다음 질문 | 통과 | 서버 저장 및 후속 TTS 완료 후 진행 |
| 12 | 5문항 완료 | 통과 | 정상·확인 불가 재질문 후 완료·멱등 finish |
| 13 | SQLite 저장 | 통과 | 실제 DB 행을 읽기 전용 직접 검사 |
| 14 | 기록 페이지 | 통과 | 목록·상세·요약·상태 조회 |
| 15 | 새로고침 유지 | 통과 | 브라우저 reload·백엔드 재시작·다른 cwd의 DB 보존 |
| 16 | 거절 기록 | 통과 | declined 행·요약·종료 시각·답변 없음 |
| 17 | 중단 기록 | 통과 | interrupted 상태·기존 답변·요약 보존 |
| 18 | 잘못된 elderId | 통과 | 문자·0·음수·소수·없는 ID 처리 |
| 19 | 서버 종료 오류 | 통과 | 실제 Uvicorn 종료 후 502·원문/순번 유지 |
| 20 | 복구 재시도 | 통과 | 실제 서버 재시작·응답 유실/시간 초과 후 중복 없는 재시도 |

6번은 실제 Web Audio 자원의 실행·정리 확인이다. 8번의 정상 TTS 순서 검증에는 제어된 음성 완료 이벤트를 사용했다. 두 항목을 실제 스피커 청감 통과로 확대 해석하지 않는다.

## 4. 기술 점검

| 항목 | 확인 결과 |
|---|---|
| CORS | localhost:5173·127.0.0.1:5173 GET/POST 및 Content-Type/Idempotency-Key 허용. 등록되지 않은 localhost:5174 preflight는 400·허용 헤더 없음 |
| REST URL | 프론트 /api 접두사 → Vite 5173의 프록시 → FastAPI 127.0.0.1:8000. 요청 URL·키·본문 프론트엔드 테스트 포함 |
| 요청/응답 형식 | 질문/어르신/대시보드/통화 시작/답변/종료/기록 목록·상세 JSON 필드와 상태코드 확인 |
| DB 경로 | 기본은 main.py 옆 backend/ansimon.db의 절대 경로. 복사한 임시 프로젝트를 다른 cwd 두 곳에서 실행해 같은 DB와 기록 유지 확인. ANSIMON_DB 절대 경로 지정 지원 |
| 초기화·보존 | 기존 DB 백업·필요 열/테이블만 추가·과거 기록 보존 회귀 테스트 통과. 누락/잘못된 DB는 health가 503으로 알리고 임의 복구하지 않음 |
| 중복 제출 | ref 잠금 + 질문/시도 순번 + SQLite 유니크 제약·트랜잭션. 동시/재전송·저장 응답 유실·본문 시간 초과 테스트 포함 |
| STT·벨소리 중복 | 시작 전 잠금, 한 세션/컨텍스트 유지, 재렌더링·늦은 콜백 검증 |
| React 초기화 | 종료 후 다시 받기로 새 통화 ID·0/5·빈 입력·빈 사용자 대화·첫 질문·오류 제거, 새 첫 질문 TTS 재생까지 확인 |
| 화면 이동 오디오 | 마이크 abort·핸들러 제거, TTS 취소, 벨소리 stop/disconnect/close, 타이머·요청 해제 |
| API 실패 원문 | 500/연결 실패/이미 저장된 응답 유실/시간 초과 모두 원문과 순번 유지·동일 요청 재시도 확인. caller AbortSignal 취소를 연결 오류로 잘못 안내하지 않음 |
| 빌드 | Vite 6.4.5, 1609개 모듈, npm run build 성공 |

## 5. 실제 수정 파일

- `backend/main.py`: DB 준비 상태를 확인하는 health 수정. 성공 응답 형식 유지, 장애 시 503.
- `frontend/src/api.js`: 요청·JSON 본문 15초 제한, 취소·연결 실패·시간 초과 구분, 기존 원문/키/오류 detail 유지.
- `backend/tests/test_final_integration.py` 추가: readiness·API JSON 계약·실제 DB 행·CORS·다른 cwd 경로 보존 검사.
- `frontend/tests/api.test.js` 추가: 시간 제한·취소·전송 형식·500/422·비 JSON 응답 검사.
- `frontend/tests/final_scenarios.py` 추가: 실제 커밋 뒤 본문 시간 초과·중복 없는 재시도·새 통화 초기화·SQLite 읽기 전용 감사.
- `frontend/tests/e2e.py`: 문서의 backend/.venv와 기존 루트 .venv 자동 탐색, 최종 시나리오 연동, 주입한 500과 예상 밖 500 분리 검사.
- `frontend/package.json`: npm test에 API 검증 포함. 의존성 버전 변경 없음.
- `README.md`: Windows PowerShell·VS Code 초보자 실행/점검/오류 해결 절차와 실제 폴더 구조로 정리. 기존의 main 푸시 예시 제거.
- `docs/conversation-flow.md`: 최신 API 시간 제한 동작과 api.js 코드 대응 추가. Mermaid 본문·SVG는 변경하지 않음.
- 이 보고서와 `docs/verification/final-*`: 수정 전 실패·기본 회귀·최종 검증 로그/JSON.

## 6. 실패·미검증·데이터 보존 범위

- **수정 전 실패:** 추가 결함 재현 4개(health 2, 시간 제한 2). 수정 후 통과.
- **최종 자동 검증 실패:** 0개. pytest에는 기존 Starlette/httpx deprecation warning 1개가 있다.
- **의도한 오류 응답:** 브라우저의 500 주입 4개, 실제 서버 중단의 502, 잘못된 요청의 4xx, DB 미준비의 503. 오류 안내와 재시도를 검증하기 위한 상황이며 정상 응답으로 위장하지 않았다.
- **실제 음성 미검증:** native Chromium에는 STT/TTS API가 있지만 오디오 입력 장치·한국어 TTS 음성은 각각 0개다. 12초 내 인식 이벤트가 오지 않았고 실제 TTS는 오류 뒤 텍스트 안내로 진행했다. 실마이크 인식, 실장치 권한 거부, 한국어 TTS·벨소리 청감은 통과로 표시하지 않는다.
- **플랫폼 미검증:** Windows PowerShell에서 직접 설치·실행하지 않았다. README 명령은 해당 플랫폼의 경로/명령 체계에 맞췄고 가상환경 활성화·전역 실행 정책 변경을 요구하지 않는다.
- **사용자 데이터:** 작업본에는 기존 사용자 DB가 포함돼 있지 않았다. 사용자 PC의 실제 DB·권한·손상 여부에 접근하지 못했다. 모든 실행 검증은 임시 DB로 수행했고 사용자 DB를 삭제하지 않았다. DB 감사는 읽기 전용 연결을 썼다. 기존 스키마·기록 보존/백업은 별도 임시 DB로 검증했다.

## 7. 사용자가 실행할 명령

[README](../README.md)의 폴더 열기·버전 확인부터 따르세요. 앱 폴더는 저장소 안 `ansimon-fullstack`입니다.

터미널 1 — 프로젝트 루트에서:

```powershell
Set-Location .\backend
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

터미널 2 — 프로젝트 루트에서:

```powershell
Set-Location .\frontend
npm.cmd ci
npm.cmd run dev
```

브라우저에서 http://127.0.0.1:5173/ 을 엽니다. health는 http://127.0.0.1:8000/api/health, 기록은 http://127.0.0.1:5173/records 입니다. API 테스트는 backend에서 `.\.venv\Scripts\python.exe -m pytest -q .\tests`, 프론트엔드는 `npm.cmd test`와 `npm.cmd run build`입니다. 브라우저 테스트 명령과 두 서버 종료 조건은 README에 있습니다.

## 8. 구현 완료와 향후 개선

현재 구현 완료: 3개 URL의 화면 분리, 웹 수신·거절·중단, Web Audio 벨소리, STT/텍스트 공통 답변 경로, TTS 질문/후속 응답, 4종 답변 분류·최대 두 번 재질문, 원문 기반 요약, SQLite 커밋·중복 방지·기록 조회·서버 재시작 보존, 입력 실패/시간 초과 재시도.

향후 개선: 실제 Windows/Chrome/Edge 마이크·한국어 음성 기기 검증, 여러 탭의 서로 다른 답변 409 충돌에 대한 사용자 동기화, 미저장 초안의 새로고침 보존, 기록 페이지네이션, 백엔드 의존성 고정 및 TestClient 경고 정리, 운영 인증·권한·DB 백업 운영. 이번 검증을 실제 전화망·의료 판단·자동 신고 기능으로 해석하지 않는다.

## 검증 원문

- [요약 JSON](verification/final-integration-summary.json)
- [최종 pytest](verification/final-integration-api.txt)
- [최종 프론트엔드 테스트](verification/final-integration-unit.txt)
- [최종 브라우저·HTTP 500·SQLite 감사](verification/final-integration-browser.txt)
- [빌드](verification/final-integration-build.txt)
- [native 음성 관측](verification/final-integration-native.json)
- [수정 전 health 실패](verification/final-before-health.txt)
- [수정 전 시간 제한 실패](verification/final-before-timeout.txt)
- 기본 회귀 로그: [API](verification/final-baseline-api.txt), [프론트엔드](verification/final-baseline-unit.txt), [브라우저](verification/final-baseline-browser.txt), [빌드](verification/final-baseline-build.txt)
