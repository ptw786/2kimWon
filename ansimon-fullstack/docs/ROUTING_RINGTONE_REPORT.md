# 화면 분리 및 전화 벨소리 구현

2026-11-09, 기존 GitHub minse 커밋 `b804693`의 안심온 프로젝트를 개선했다.

## 화면과 동작

- `/`: 기존 로고·사이드바·오늘 현황·어르신 목록·완료/미완료 상태를 유지한 생활지원사 대시보드. 각 어르신의 전화 체험 버튼은 `/call/{id}`로 이동한다.
- `/call/:elderId`: 관리 사이드바 없는 어르신 전화 화면. 발신자 ‘안심온 돌봄전화’, 초록색 수신·빨간색 거절, 연결 후 경과 시간·질문·답변·마이크·텍스트 답변·종료 버튼을 표시한다. 전화 버튼 100px, 주요 본문 22px, 발신자 31~36px로 구성했다. 모바일에서도 한 열로 표시한다.
- `/records`: 기존 DB에서 읽은 날짜·시간·어르신 이름·완료/거절/중단 상태·요약·상세 모달을 표시한다. 상세 조회 중 로딩·오류·재시도를 지원하고 Escape로 닫을 수 있다.
- React Router로 직접 URL 접근, 새로고침, 뒤로 가기, 존재하지 않는 경로를 처리한다. 새 라우팅 의존성은 lockfile에 포함했다.

## 벨소리 및 리소스

`useRingtone`은 Web Audio API의 실제 AudioContext 1개, sine oscillator 2개(440/480Hz), gain 1개, cadence 타이머 1개를 사용한다. 0.8초 울림을 두 번 낸 뒤 쉬는 4초 주기다. gain은 0.045로 설정하고 완만한 시작·종료를 적용했다. 외부 음원과 유료 API는 사용하지 않는다.

AudioContext가 suspended 상태이거나 resume 요청이 차단되면 ‘벨소리 켜기’를 표시한다. resume Promise가 자동 재생 정책 때문에 미해결 상태로 남아도 화면을 막지 않는다. 버튼을 누르면 같은 컨텍스트의 resume을 다시 시도한다. Web Audio 미지원·초기화 실패도 안내하며 수신·거절은 사용할 수 있다.

수신·거절 버튼 클릭 즉시 벨소리를 멈추며 API 처리 중에는 다시 시작하지 않는다. 성공하면 통화 중/종료 화면으로 이동한다. 요청에 실패해 다시 수신 대기가 되면 벨소리도 재개할 수 있다. 화면 이탈·수신·거절·종료·리셋 시 반복 타이머 해제, oscillator stop/disconnect, gain disconnect, AudioContext close를 수행한다. 늦게 resolve된 resume 콜백은 폐기된 세션을 다시 실행하지 않는다. 재렌더링만으로 컨텍스트를 새로 만들지 않는다.

## API·진행 상태 보존

백엔드와 DB 스키마는 이번 단계에서 변경하지 않았다. 이전 HTTP 500 수정·DB 백업·답변 순번·요청 키·멱등 종료 처리를 그대로 사용한다.

- 수신/거절은 ref 기반 동기 busy 잠금으로 연속 클릭을 막는다. 백엔드의 중복 방지도 유지한다.
- 요청 키는 sessionStorage에 보관하여 응답 유실·화면 재진입 시 같은 수신 시도를 식별한다. 새 체험은 새 키를 사용한다.
- 시작 응답 유실 후 ‘다시 시도’하면 DB의 진행 중 통화를 불러온다. 같은 통화를 중복 생성하지 않는다.
- 마지막 답변 저장 후 종료 요청 실패 시 ‘완료 저장’으로 재시도한다.
- 잘못된 elderId, 없는 어르신, 로딩, API 오류를 표시한다. 유효한 어르신 확인 전에는 수신 버튼과 벨소리를 생성하지 않는다.
- 화면 이탈 시 AbortController로 요청을 취소하고 타이머·TTS·음성 인식을 정리한다. 취소는 서버에 이미 커밋된 요청을 되돌리지 않는다. 진행 중 통화는 서버에 보존되고 같은 URL에서 복원한다. 화면 이탈을 자동 중단으로 기록하지 않는다.
- 통화 종료 후 같은 화면에서 다시 받으면 새 통화 ID·답변 수·메시지·입력·시간·오류 상태로 초기화한다.

## 실제 수정 파일

기존 파일 변경:

- `frontend/src/App.jsx`: 3개 URL의 Router 및 관리 화면 layout.
- `frontend/src/api.js`: AbortSignal 전달과 요청 취소 구분. 기존 오류 상세·멱등 키 전달 유지.
- `frontend/src/styles.css`: 기존 스타일 유지, 링크 메뉴와 어르신 전용 큰 글씨·버튼·반응형 스타일 추가.
- `frontend/package.json`, `frontend/package-lock.json`: React Router 추가.
- `frontend/tests/e2e.py`: 기존 실제 API·저장 회귀 검증을 새 URL 구조에 맞추고 전화·벨소리 검증 확장.
- `README.md`: 경로, 구조, 사용법·검증 안내.

추가 파일:

- `frontend/src/pages/DashboardPage.jsx`, `CallPage.jsx`, `RecordsPage.jsx`
- `frontend/src/components/Sidebar.jsx`, `Common.jsx`, `Feedback.jsx`, `IncomingCall.jsx`, `ActiveCall.jsx`, `CallControls.jsx`, `ConversationPanel.jsx`, `TextAnswerInput.jsx`
- `frontend/src/hooks/useCall.js`, `useRingtone.js`, `useResource.js`
- `frontend/tests/audio_probe.js`
- 이 보고서 및 `docs/verification/routing-*.txt`

## 테스트 결과

- 기존 백엔드 pytest **8개 통과**. OS 시간대 DB 없는 실행, 통화 전체 흐름, 동시·재전송 중복 방지, 기존 DB 백업·보존, 서버 재실행, CORS, 오류 응답 검증을 유지했다. Starlette/httpx deprecation warning 1개가 있다.
- `npm run build` **통과**. React/Vite 1606개 모듈 변환.
- 실제 Uvicorn + Vite + Chromium 자동 검증 **12개 시나리오 묶음 통과**:
  1. 백엔드 중단 시 설명 있는 502.
  2. 서버 시작 후 실제 API 재호출과 어르신 목록.
  3. 대시보드 단독 장애 시 목록 독립 조회.
  4. 별도 어르신 URL, 실제 Web Audio 실행, 수신 즉시 노드 정리.
  5. 5문항·시간 표시·진행 중 URL 새로고침 복원·종료 커밋 후 응답 유실 재시도·요약 저장.
  6. 잘못된/없는 elderId와 미등록 경로.
  7. 차단 상태 주입 후 벨소리 버튼, 재렌더링·다음 벨소리 주기의 단일 컨텍스트, 낮은 gain, 모바일 큰 버튼, 거절·다시 받기·화면 이동 정리.
  8. 연속 수신 클릭 시 단일 통화, 답변 후 중단 저장, 관리 화면 왕복 후 복원.
  9. 화면 이동 시 진행 중 조회 취소, 화면 이탈 시 오디오 및 통화 타이머 해제, 기록 URL 새로고침 보존.
  10. 질문 API 500 후 재시도, 시작 커밋 후 응답 유실 복원과 중복 방지.
  11. Web Audio 미지원 안내와 수신 버튼 유지.
  12. 브라우저 새로고침·백엔드 재시작 후 기록 동일, 브라우저 JavaScript 예외 없음.

브라우저의 자동 재생 정책은 실행 환경마다 다르므로, 차단 시나리오는 native AudioContext를 suspend하고 resume 허용 조건만 테스트에서 제어했다. 해당 테스트를 실제 OS 자동 차단을 관측한 것으로 표현하지 않는다. 목록/저장/기록에는 실제 FastAPI와 SQLite를 사용했고, 대시보드/질문 500 및 응답 유실은 명시적 장애 주입이다. 요청 취소 검증은 질문 조회 Promise만 보류시킨 뒤 AbortSignal을 확인했다. 실제 오디오의 상태·노드·gain·stop/disconnect/close를 검사했으며 스피커를 통한 청감 평가는 하지 않았다. 데스크톱 통화 화면과 390px 모바일 수신 화면을 캡처해 시각적으로 확인했다.

## 실행 및 남아 있는 제한

기존처럼 백엔드를 8000, Vite 개발 서버를 5173에서 실행하면 된다. `/call/1` 또는 `/records`를 직접 열거나 대시보드의 전화 체험 버튼으로 이동할 수 있다. 통화 기록이 있는 기존 DB는 삭제하지 않는다.

마이크·한국어 TTS는 OS·권한·브라우저에 따라 다르며 실제 음성 인식 정확도는 이번 자동 검증에 포함하지 않았다. Safari/Firefox의 실기기 청감·정책 검증도 별도 확인 사항이다. 정적 서버에 배포하려면 `/call/*`, `/records`를 `index.html`로 전달하는 SPA fallback과 기존 `/api` 프록시 설정이 필요하다. 이번 검증은 Vite 개발 서버 + FastAPI 기준이다.
