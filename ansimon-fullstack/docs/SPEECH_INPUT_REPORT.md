# STT·TTS 및 텍스트 대체 입력 안정화

2026-11-09. 기존 React + FastAPI + SQLite, 규칙 기반 대화·재질문·벨소리·기록 저장을 유지했다. 이번 단계에서 백엔드 코드와 DB 스키마는 변경하지 않았다. OpenAI·유료 음성 API 및 새로운 외부 라이브러리를 추가하지 않았다.

## 구현

### 공통 답변 처리

음성·텍스트·빠른 답변·저장 재시도는 모두 `useCall.js`의 **하나의 `submitAnswer()`**를 사용한다. `/api/calls/{id}/turns`를 쓰는 프론트엔드 저장 경로도 이 함수 한 곳이다.

```text
SpeechRecognition 결과 → 확정 텍스트 → submitAnswer() → 기존 FastAPI → SQLite
키보드/Enter/보내기/빠른 답변 ────────────┘
```

빈 문자열·공백·500자 초과를 저장 전에 차단한다. STT의 긴 텍스트는 입력창에 남겨 수정할 수 있다. 입력 잠금·동기 busy ref·서버의 질문/재질문 순번으로 중복 제출을 막는다. 서버 저장 성공 전에는 다음 질문으로 이동하지 않는다. 저장 실패 시 원문과 전송 순번을 유지하고 같은 답변으로 재시도한다. 저장 여부가 불확실한 답변은 편집을 잠가 덮어쓰지 않는다. 화면 이탈/새로고침까지 미저장 초안을 영구 저장하는 기능은 이번 범위에 추가하지 않았다.

### STT

`SpeechInput`이 브라우저의 `SpeechRecognition`을 우선 사용하고 없으면 `webkitSpeechRecognition`으로 대체한다.

- `lang='ko-KR'`, `continuous=false`, `interimResults=true`, `maxAlternatives=1`.
- 상태는 idle/starting/listening. **start 호출 전**에 세션을 잠가 onstart 전의 연속 클릭도 중복 실행하지 않는다.
- 중간 결과는 화면의 ‘인식 중’에만 표시한다. 최종 결과를 ‘최근 인식 결과’에 보여 주고 공통 submitAnswer로 한 번만 전송한다.
- 수동 중지는 abort와 핸들러 해제로 구현한다. 중지 뒤 도착한 final/error/end 이벤트는 무시하고 임시 발화를 자동 제출하지 않는다.
- 텍스트를 작성하기 시작하면 활성 마이크를 중단하므로 늦은 인식 결과가 타이핑한 내용을 덮어쓰지 않는다.
- 권한 거부(`not-allowed`), 서비스 불가, 마이크 없음, 무음, 네트워크 오류, 언어 미지원, 시작 예외, HTTPS/localhost 조건을 각각 한국어로 안내한다. 텍스트 대화는 유지한다.
- 시작/결과 이벤트가 오지 않는 경우 30초 제한으로 세션을 해제하고 텍스트 대체를 안내한다. 그 전에도 마이크 중지와 텍스트 입력은 사용할 수 있다.
- 통화 종료·화면 이탈·TTS 시작 시 인식을 해제한다. 일회성 세션 객체와 identity 검사로 오래된 콜백의 재제출을 막는다.

### TTS

`SpeechOutput`이 단일 SpeechSynthesisUtterance와 타이머를 소유한다. 한국어 음성이 있으면 선택하고 항상 `lang='ko-KR'`를 지정한다.

- 실제 speak 직전에 STT를 반드시 중단한다.
- 질문·후속 응답·종료 인사 순서를 onend/onerror 기반 Promise로 연결한다. 말하는 동안 새 답변을 받지 않는다.
- 통화 ID·질문 순번·재답변 순번·발화 종류로 키를 만든다. 같은 대화 단계의 중복 요청은 같은 Promise/완료 결과를 사용한다. 정당한 재질문은 다른 키이므로 같은 문장을 다시 읽을 수 있다.
- 음성 끄기는 현재 발화를 취소하고 텍스트로 진행한다. 음성을 다시 켜면 이후 단계에 적용하며 이미 처리된 문장을 자동 재생하지 않는다.
- 통화 종료 시 현재 발화와 완료 콜백을 무효화한다. TTS 중에도 종료할 수 있고 이미 저장된 답변은 보존한다.
- 재생 실패·미지원·완료 이벤트 지연에는 텍스트 안내를 표시한다. 타이머·이벤트 핸들러는 종료/해제 시 정리한다.

### 텍스트 UI

항상 현재 질문과 답변 입력창·보내기 버튼을 제공한다. Enter 제출, 한국어 IME 조합 중 Enter 차단, 키 반복 및 중복 제출 방지, ‘저장 중…’과 aria-busy 상태를 추가했다. 음성 인식 오류는 API 저장 오류와 분리해 표시한다. STT를 사용할 수 없어도 모든 문항을 텍스트로 완료할 수 있다.

## 실제 변경 파일

| 파일 | 역할 |
|---|---|
| `frontend/src/speech/recognition.js` (추가) | STT 세션, 상태·오류·시간 제한·중지·콜백 정리 |
| `frontend/src/speech/synthesis.js` (추가) | TTS 순서·중복 방지·한국어 음성·취소·해제 |
| `frontend/src/hooks/useCall.js` | 두 입력의 공통 submitAnswer, 컨트롤러 연동, 입력 보존·제출 상태 |
| `frontend/src/components/SpeechInputStatus.jsx` (추가) | 연결/인식 상태, 중간·최종 텍스트, 오류 안내 |
| `frontend/src/components/TextAnswerInput.jsx` | 버튼/Enter, IME 보호, 로딩·제출 잠금 |
| `frontend/src/components/ActiveCall.jsx` | 마이크 시작·중지 및 상태 표시 |
| `frontend/src/components/ConversationPanel.jsx` | 현재 질문, STT 결과·상태·텍스트 입력 |
| `frontend/src/pages/CallPage.jsx` | 공통 submitAnswer 연결 |
| `frontend/src/styles.css` | 상태·인식 결과·저장 중 표시 |
| `frontend/package.json` | `npm test` 명령 추가(의존성 추가 없음) |
| `frontend/tests/speech.test.js` (추가) | Node 자동 테스트 |
| `frontend/tests/speech_input_scenarios.py` (추가) | UI·실제 서버 중단/복구 및 native API 관측 |
| 기존 `frontend/tests/speech_probe.js`, `conversation_scenarios.py`, `e2e.py` | 확정/중간 이벤트와 새 검증 연동 |
| `README.md`, 이 보고서, `docs/verification/speech-*` | 실행·검증 안내와 로그 |

## 자동 테스트 결과

- **Node 단위 테스트 28개 통과**, `npm test`. 가짜 인식기/합성기/시계로 중복 시작, 중간·최종 결과, 늦은 콜백, 수동 중지, 권한/서비스/네트워크/무음 오류, webkit 대체, 미지원, 한국어 옵션, TTS 취소·중복·시간 제한·해제를 검증했다.
- **기존 백엔드 pytest 70개 통과**. FastAPI·규칙 분류·DB 보존·재질문·멱등 저장의 회귀 검증이다. 기존 Starlette/httpx deprecation warning 1개가 있다.
- **Playwright 브라우저 시나리오 25개 묶음 통과**. 실제 React/Vite·Uvicorn·SQLite를 사용했다. 기존 18개 회귀 + 이번 6개 STT/TTS·텍스트 시나리오 + native 브라우저 관측/텍스트 대체 1개다.
- **`npm run build` 통과**. React/Vite 1609개 모듈 변환.

브라우저 자동 테스트에서 정상 인식 결과·권한 거부·미지원·STT 오류·TTS 완료/오류는 **명시적으로 이벤트를 주입**했다. 실제 마이크로 발화를 인식했다고 주장하지 않는다. API 장애 검증은 Uvicorn을 실제 종료했다가 같은 임시 DB로 재시작하여 수행했다. 로딩 검증에는 HTTP 전달을 일시 보류했고, 재시도/저장은 실제 FastAPI를 사용했다. 음성 실패를 가짜 성공 응답으로 바꾸지 않았다.

| 요구 상황 | 자동 재현·검증 |
|---|---|
| 정상 음성 인식 | 한국어 옵션, 중간 결과 표시, 확정 결과 1회 제출·저장, 늦은 중복 이벤트 무시 |
| 마이크 권한 거부 | not-allowed 이벤트·시작 예외 안내, 텍스트로 5문항 완료 |
| STT 미지원 | 두 생성자 부재 시 안내, 텍스트로 5문항 완료 |
| 텍스트 5문항 | 버튼·Enter·빈 값·IME 보호, 실제 저장·완료 |
| 통화 중 마이크 중단 | 시작 중/인식 중 수동 중지, 도중 종료, 타이핑 시 중단, 늦은 결과 폐기 |
| 통화 중 TTS 중단 | STT 비활성화, 음성 끄기·켜기, 발화 중 종료, 콜백 무효화 |
| API 연결 실패 | 실제 Uvicorn 중단 후 오류·원문·질문 순번 유지 |
| 서버 복구 후 재시도 | 실제 재시작 후 같은 답변을 1회 저장 |
| 완료 후 기록 조회 | 실제 목록·상세·원문·상태 확인 |
| 새로고침 후 유지 | `/records` 재접속 후 SQLite 기록 확인 |

## 실제 브라우저 API 관측 — 성공한 것과 미검증 범위

추가 Chromium 페이지에서는 SpeechRecognition/SpeechSynthesis를 가짜 구현으로 교체하지 않았다. 원래 생성자로 실제 객체를 만들고 이벤트를 관찰했다. Playwright로 브라우저를 조작한 검증이며 사람이 마이크로 말한 수동 테스트는 아니다.

관측 환경: `SpeechRecognition/webkitSpeechRecognition` 존재, `SpeechSynthesis` 존재, **오디오 입력 장치 0개**, **한국어 합성 음성 0개**. 실제 인식기에 ko-KR을 설정하고 start를 호출했지만 12초 관측 동안 start/result/error/end 이벤트가 오지 않았다. 수동 중지 후 텍스트 대체로 진행했다. 네트워크나 권한 문제가 원인이라고 임의로 단정하지 않는다. 실제 TTS는 재생 실패 안내가 표시되어 텍스트로 전환했다.

따라서 이 환경에서 **실마이크의 정상 한국어 인식, 실장치 권한 거부, 실제 한국어 음성 청감은 미검증**이다. 이를 통과로 표시하지 않는다. 반면 동일한 실제 브라우저 페이지에서 텍스트로 다섯 질문을 완료하고 실제 FastAPI/SQLite 기록과 새로고침 보존은 확인했다. 화면의 현재 질문·중간 인식·음성 대체 안내도 캡처해 확인했다.

원시 관측은 `docs/verification/speech-native.json`, 자동 테스트 로그는 `speech-unit.txt`, `speech-api.txt`, `speech-e2e.txt`, `speech-build.txt`에 보관했다.

## 실행과 기기 확인 방법

기존 backend/FastAPI와 frontend/Vite 실행 방법을 그대로 사용한다. 프론트엔드 단위 테스트는 frontend에서 `npm test`, API 테스트는 프로젝트 루트에서 `.venv/bin/python -m pytest -q backend/tests`, 전체 브라우저 테스트는 `python frontend/tests/e2e.py`다. Windows 가상환경 경로는 README를 따른다.

선택 환경 변수 `ANSIMON_NATIVE_REPORT`로 native 관측 JSON 저장 경로, `ANSIMON_SCREENSHOT_DIR`로 화면 캡처 폴더를 지정할 수 있다. 기본 테스트는 소스 폴더에 관측 파일을 자동 생성하지 않는다.

실제 마이크와 한국어 음성이 있는 Chrome/Edge 기기에서 localhost 또는 HTTPS로 열고, 주소창의 마이크 허용/거부를 각각 확인해야 한다. 브라우저 제공 STT는 브라우저 사업자의 네트워크 서비스에 의존할 수 있다. 이번 구현은 별도의 API 키·유료 계정·과금 API를 사용하지 않는다.
