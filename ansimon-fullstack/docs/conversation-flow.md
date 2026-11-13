# 안심온 STT → 규칙 기반 대화 → 통화 기록 흐름

기준: 2026-11-09, `minse`의 앱 소스 커밋 `54e3163`. React·Web Speech API, FastAPI·규칙 엔진, SQLite를 구분했다. 아래 실선과 점선은 모두 **현재 구현된 처리**이며, 점선은 도중 종료 또는 오류 경로다. 여기서 ‘AI’는 유료 API/LLM이 아닌 규칙 기반 응답을 뜻한다.

[전체 흐름 SVG](conversation-flow.svg) · [답변 저장 상세 SVG](conversation-flow-storage.svg)

## 1. 전화 수신부터 생활지원사 기록 조회까지

신규 통화를 기준으로 그렸다. 기존 진행 중 통화가 있으면 수신 화면과 벨소리를 건너뛰고 저장된 답변·재질문 횟수·현재 질문을 복원한다. 잘못된 elderId나 초기 조회 오류에는 안내를 표시하고 통화를 시작하지 않는다.

```mermaid
flowchart TB
  subgraph REACT["React 프론트엔드 · 브라우저"]
    direction TB
    R_in["전화 수신 화면<br/>/call/:elderId"]
    R_ring["Web Audio 벨소리 재생 시도"]
    R_ring_alt["자동 재생 차단: 벨소리 켜기 버튼<br/>미지원: 무음 안내 · 수신/거절 가능"]
    R_pick{"수신 또는 거절"}
    R_accept["수신: 벨소리 중단<br/>통화 시작 요청"]
    R_decline["거절: 벨소리 중단<br/>거절 기록 요청"]
    R_start_error["시작/거절 오류 안내<br/>상태 재조회 또는 같은 키로 재시도"]
    R_active["AI 웹통화 시작"]
    R_question["현재 질문 표시<br/>STT 중단 후 질문 TTS · ko-KR"]
    R_input{"음성 또는 텍스트 입력"}
    R_stt["STT · ko-KR<br/>중간 결과 표시 → 확정 텍스트"]
    R_stt_error["STT 오류/중지 안내<br/>권한 거부·미지원·무음 등<br/>마이크 중단 · 텍스트로 대체"]
    R_text["텍스트 입력<br/>전송 버튼 또는 Enter"]
    R_submit["공통 submitAnswer<br/>빈 값·길이·중복 검사 후<br/>원문 + 질문/시도 순번 전송"]
    R_answer_error["API/저장 오류: 원문·순번 보존<br/>다시 시도로 동일 답변 재전송"]
    R_reply["저장 성공 응답 반영<br/>분류·후속 응답 표시 및 TTS"]
    R_next{"서버 응답으로 다음 단계 판단"}
    R_farewell["5문항 확정<br/>마지막 후속 응답 후 종료 인사 TTS"]
    R_stop["사용자가 도중 종료<br/>STT·TTS 중단"]
    R_finish["통화 종료 요청<br/>completed 또는 interrupted"]
    R_finish_error["종료 저장 실패 안내<br/>종료/완료 저장 버튼으로 재시도"]
    R_ended["종료 화면 · 오디오 자원 정리"]
    R_records["생활지원사 기록 화면<br/>/records · 목록/상세 요청"]
    R_view["어르신 이름·날짜·상태·요약<br/>실제 답변·분류·재질문 내용 표시"]
    R_read_error["기록 조회 오류 안내<br/>목록/상세 다시 시도"]
  end

  subgraph API["FastAPI 백엔드 · 무료 규칙 기반 대화"]
    direction TB
    B_start["통화 시작 검증<br/>어르신·진행 중 통화·중복 키 확인"]
    B_decline["거절 요청 검증<br/>어르신·중복 키 확인"]
    B_answer["답변 검증·중복/순번 확인<br/>규칙 기반 분류 + 후속 응답 생성<br/>재질문/문항 확정 결정"]
    B_finish["종료 요청 검증<br/>확정된 실제 답변만 사용해 요약 생성"]
    B_read["기록 조회 API<br/>GET /api/calls<br/>GET /api/calls/:id"]
  end

  subgraph DB["SQLite · 영구 저장/조회"]
    direction TB
    D_start[("calls: in_progress 저장")]
    D_decline[("calls: declined 저장<br/>수신 거절 요약")]
    D_answer[("turn_attempts: 답변·판정·후속 응답<br/>확정 문항만 turns에 추가<br/>하나의 트랜잭션으로 커밋")]
    D_finish[("calls: 종료 시각·상태·요약 갱신<br/>커밋 후 성공 응답")]
    D_read[("calls·residents·turns·turn_attempts 조회")]
  end

  R_in --> R_ring
  R_ring -->|재생 가능| R_pick
  R_ring -->|차단/미지원| R_ring_alt
  R_ring_alt --> R_pick
  R_ring_alt -->|벨소리 켜기 클릭| R_ring
  R_pick -->|수신| R_accept
  R_pick -->|거절| R_decline
  R_accept -->|POST /api/residents/:id/calls| B_start
  B_start --> D_start --> R_active --> R_question
  R_decline -->|POST /api/residents/:id/decline| B_decline
  B_decline --> D_decline --> R_ended
  B_start -.->|오류| R_start_error
  B_decline -.->|오류| R_start_error
  D_start -.->|저장 실패| R_start_error
  D_decline -.->|저장 실패| R_start_error
  R_start_error -->|재조회/다시 선택| R_pick
  R_start_error -->|진행 중 통화 복원| R_question

  R_question -->|발화 완료 · 음성 끔/재생 오류는 텍스트 안내| R_input
  R_input -->|음성| R_stt
  R_input -->|키보드| R_text
  R_stt -->|확정 결과 1회| R_submit
  R_stt -.->|실패 또는 수동 중지| R_stt_error
  R_stt_error --> R_text
  R_text --> R_submit
  R_submit -->|빈 값/길이 초과: 전송 안 함| R_text
  R_submit -->|POST /api/calls/:id/turns| B_answer
  B_answer -->|새 답변| D_answer
  B_answer -->|동일 요청: 저장된 결과 재사용| R_reply
  D_answer -->|커밋 성공| R_reply
  R_submit -.->|연결 실패/응답 유실| R_answer_error
  B_answer -.->|검증/충돌 오류| R_answer_error
  D_answer -.->|저장 실패: 롤백| R_answer_error
  R_answer_error -->|동일 원문·순번으로 재시도| R_submit
  R_reply -->|후속 응답 TTS 완료 또는 텍스트 대체| R_next
  R_next -->|확인 불가 · 재질문 2회 미만: 같은 질문| R_question
  R_next -->|문항 확정 · 남은 질문 있음| R_question
  R_next -->|5문항 확정| R_farewell
  R_farewell --> R_finish
  R_input -->|도중 종료| R_stop
  R_question -.->|TTS 중 종료| R_stop
  R_reply -.->|TTS 중 종료| R_stop
  R_stop --> R_finish
  R_finish -->|POST /api/calls/:id/finish| B_finish
  B_finish --> D_finish --> R_ended
  R_finish -.->|연결 실패| R_finish_error
  B_finish -.->|검증 오류| R_finish_error
  D_finish -.->|저장 실패: 롤백| R_finish_error
  R_finish_error --> R_finish
  R_ended --> R_records
  R_records --> B_read --> D_read --> R_view
  B_read -.->|조회 오류| R_read_error
  D_read -.->|조회 실패| R_read_error
  R_records -.->|연결 실패| R_read_error
  R_read_error --> R_records

  classDef front fill:#edf5ff,stroke:#4279b8,color:#17344f;
  classDef server fill:#e9f8f2,stroke:#338365,color:#153d31;
  classDef store fill:#fff5df,stroke:#b9892d,color:#513c13;
  classDef error fill:#fff0ed,stroke:#bb5b4c,color:#702b21;
  class R_in,R_ring,R_pick,R_accept,R_decline,R_active,R_question,R_input,R_stt,R_text,R_submit,R_reply,R_next,R_farewell,R_stop,R_finish,R_ended,R_records,R_view front;
  class B_start,B_decline,B_answer,B_finish,B_read server;
  class D_start,D_decline,D_answer,D_finish,D_read store;
  class R_ring_alt,R_start_error,R_stt_error,R_answer_error,R_finish_error,R_read_error error;
```

**처리 순서 주의:** `assess()`가 답변 분류와 후속 응답을 먼저 만든다. 그 결과를 답변 원문과 함께 저장한 뒤 프론트엔드가 후속 응답을 읽는다. 따라서 ‘저장 후에 후속 응답을 생성’하는 구조로 그리지 않았다. 종료도 ‘종료 요청 → 요약 생성 → 상태·요약 커밋 → 종료 화면’ 순서다.

## 2. 답변 판정·재질문·중복 저장 방지 상세

```mermaid
flowchart TB
  subgraph CLIENT["React · 공통 답변 경로"]
    C_send["STT 확정 결과 / 텍스트<br/>submitAnswer → answer, index, attempt"]
    C_ok["커밋 성공 응답 수신<br/>후속 응답 TTS → 같은 질문/다음 질문/종료"]
    C_error["오류 안내 · 원문/순번 유지<br/>저장 실패 시 동일 요청 재시도"]
  end
  subgraph BACKEND["FastAPI · main.py / conversation.py"]
    V_shape{"답변 1~500자·공백 아님<br/>질문/시도 범위 유효?"}
    V_call{"통화가 존재하는가?"}
    V_key{"중복 요청 키가<br/>다른 질문/시도와 충돌?"}
    V_old{"이미 저장된<br/>같은 질문/시도인가?"}
    V_same{"같은 답변 원문인가?"}
    V_state{"진행 중 통화이며<br/>현재 질문/시도 순번과 일치?"}
    V_rule["질문별 규칙 판정<br/>긍정 / 부정 / 중립 / 확인 불가"]
    V_urgent{"긴급 표현인가?"}
    V_help["부정 확정 · 직접 119 연락 안내 생성<br/>실제 자동 신고는 수행하지 않음"]
    V_retry{"확인 불가이고<br/>현재 attempt가 2 미만인가?"}
    V_repeat["문항 수 유지 · 재질문 횟수 증가<br/>같은 질문 · 다음 attempt"]
    V_final["문항 확정 · 문항 수 1 증가<br/>다음 질문 또는 5문항 완료<br/>세 번째 불명확 답변은 확인 불가 확정"]
    V_reply["후속 응답 및 반환 JSON 확정"]
    V_422["422 · 입력 오류"]
    V_404["404 · 없는 통화"]
    V_409["409 · 다른 답변/키/순번 충돌 또는 종료된 통화"]
    V_500["500 · 저장 오류 · 트랜잭션 롤백"]
  end
  subgraph SQLITE["SQLite · 쓰기는 BEGIN IMMEDIATE로 직렬화"]
    S_read[("calls·turns·turn_attempts 조회")]
    S_replay[("저장된 result_json 반환<br/>행 추가·재질문 횟수 증가 없음")]
    S_write[("turn_attempts에 모든 시도 저장<br/>문항 확정 시에만 turns 저장<br/>원문·판정·reply·result_json 원자 커밋")]
  end

  C_send --> V_shape
  V_shape -->|아니오| V_422 --> C_error
  V_shape -->|예| V_call
  V_call -->|아니오| V_404 --> C_error
  V_call -->|예| S_read --> V_key
  V_key -->|충돌| V_409
  V_key -->|충돌 없음/키 생략| V_old
  V_old -->|예| V_same
  V_same -->|같음| S_replay --> C_ok
  V_same -->|충돌| V_409 --> C_error
  V_old -->|아니오| V_state
  V_state -->|아니오| V_409
  V_state -->|예| V_urgent
  V_urgent -->|예| V_help --> V_retry
  V_urgent -->|아니오| V_rule --> V_retry
  V_retry -->|예: 최초 답변 또는 첫 재답변| V_repeat --> V_reply
  V_retry -->|아니오| V_final --> V_reply
  V_reply --> S_write
  S_write -->|커밋 성공| C_ok
  S_write -.->|실패| V_500 --> C_error
  C_error -->|저장 여부 불명/서버 복구 후 재시도| C_send

  classDef front fill:#edf5ff,stroke:#4279b8,color:#17344f;
  classDef store fill:#fff5df,stroke:#b9892d,color:#513c13;
  classDef error fill:#fff0ed,stroke:#bb5b4c,color:#702b21;
  class C_send,C_ok front;
  class S_read,S_replay,S_write store;
  class C_error,V_422,V_404,V_409,V_500 error;
```

- `index`는 0~4, `attempt`는 최초 답변 0·재답변 1·재답변 2다. 최대 두 번 재질문하므로 답변 기회는 세 번이다. 중간 STT 결과나 빈 답변은 서버 시도로 저장하지 않는다.
- 새 답변의 규칙 판정 안에서 긴급 표현을 우선 검사한다. 긴급 표현은 부정으로 확정하고 안내문을 만들며, 일반 문항 분류보다 우선한다. 위 그림의 긴급 분기는 이 판정 내부 처리를 풀어 쓴 것이다.
- `(call_id, question_index, attempt)` 유니크 제약과 쓰기 트랜잭션으로 동시/중복 저장을 막는다. 같은 순번·원문 재전송은 기존 응답을 반환하고 횟수를 소모하지 않는다.
- 선택 `Idempotency-Key` 충돌은 기존 답변 재사용 여부보다 먼저 확인한다. 키 충돌과 같은 순번의 다른 원문은 모두 409다.
- 모든 문항이 확인 불가여도 세 번씩의 답변 기회를 마치면 5문항 완료 상태로 종료할 수 있다. 완료는 ‘모든 답변이 긍정/건강 정상’이라는 의미가 아니다.

## 3. 오류·종료·조회 경로의 실제 동작

| 상황 | 현재 처리 |
|---|---|
| 잘못된 elderId / 어르신 없음 | 안내 화면. 수신 버튼·벨소리·통화 저장을 만들지 않음. 초기 API 실패는 다시 시도 가능. |
| 기존 진행 중 통화 | 같은 어르신의 통화를 조회하고 현재 질문·저장 답변·재질문 횟수를 복원. 수신 벨소리를 다시 울리지 않음. |
| 벨소리 차단/미지원 | 차단 시 ‘벨소리 켜기’, 미지원 시 안내. 무음 상태에서도 수신·거절 가능. |
| STT 권한 거부/무음/미지원/네트워크 오류 | 한국어 안내 후 텍스트 대체. 사용자는 마이크 재시작도 가능. 확정 결과만 공통 submitAnswer로 전달. |
| TTS 끄기/미지원/재생 오류/완료 이벤트 지연 | 텍스트 안내로 진행. TTS 발화 전 STT를 중단하고, 같은 대화 단계의 중복 발화를 막음. |
| 빈 값·500자 초과·한국어 조합 중 Enter | 프론트엔드에서 제출 방지. 백엔드도 빈 값·길이·순번을 검증하며 잘못된 요청을 성공으로 바꾸지 않음. |
| 답변 연결 실패/저장 실패/응답 유실/시간 초과 | 현재 화면에 전송 원문·순번 보존. 요청·응답 본문은 15초 제한 후 동일 요청 재시도. 서버에서 이미 커밋됐다면 기존 결과 반환. 저장 여부 불명인 입력은 편집을 잠금. |
| 409 충돌 | 자동 성공 처리하지 않음. 동일 요청으로도 해결되지 않는 다른 답변/순번 충돌은 화면에 계속 표시됨. 화면을 나갔다 같은 통화에 재진입하면 서버 상태를 복원. |
| 저장 중 종료 버튼 | 중복 동작을 막기 위해 API 처리 중 잠금. TTS 중에는 종료 가능하며 발화를 취소함. |
| 5문항 종료 | 마지막 후속 응답·종료 인사 TTS 후 completed 종료 요청. 실패하면 ‘완료 저장’으로 재시도. |
| 도중 종료 | STT·TTS를 멈추고 interrupted 종료 요청. 이미 저장된 답변을 유지하여 요약·종료 상태 저장. |
| 거절 | 별도 decline API가 calls에 declined·종료 시각·‘수신 거절’을 기록. 5문항 대화나 별도 AI 요약 단계는 실행하지 않음. |
| 종료 요청 재전송 | 이미 같은 상태로 종료됐으면 기존 결과 반환. 다른 종료 상태 변경은 409. |
| 단순 화면 이동/새로고침 | 요청·벨소리·STT·TTS·타이머 정리. 화면 이동 자체가 자동 통화 종료 요청은 아님. DB의 in_progress 통화는 재진입 시 복원. 아직 저장되지 않은 입력의 새로고침 보존은 미구현. |
| 기록 조회 | `/records`에서 목록과 상세 조회. 통화 시작부터 calls 행이 존재하므로 진행 중 통화도 조회할 수 있음. 목록 기본 최근 100개, 최대 500개 제한 유지. |

### 요약 생성 기준

`finish_call()`이 `summary_for()`로 **최종 분류가 긍정·부정·중립인 저장 답변의 실제 원문**을 연결한다. 확인 불가 원문·미확정 시도·과거 미분류 원문을 새 요약의 확인 내용에 넣지 않는다. 확인 불가 항목 이름은 별도로 표시한다. 의학적 진단을 만들지 않고, 긴급 표현에는 ‘직접 119 연락 안내문 생성·자동 신고 없음’만 기록한다. 실제 119 신고·전화 발신을 했다고 표시하지 않는다. 과거 완료 통화의 기존 요약을 소급 재작성하지 않는다.

### 구현 범위와 계획 구분

흐름도에는 구현된 웹 통화만 포함했다. 실제 전화망 발신/수신, LLM/OpenAI 대화 생성, 자동 119 신고, 미저장 초안의 영구 복원은 구현되지 않았으며 흐름도에 실행 단계로 넣지 않았다. 계획·준비 단계 항목은 현재 실행 흐름과 분리한다.

- **기존 README에 적힌 후속 준비 항목:** 사용자 로그인·접근 권한, 실제 전화/문자 사업자 연동, 운영 DB·배포·보존 정책 정비. [README의 후속 출시 준비 체크](../README.md)를 참고하며, 현재 구현으로 표시하지 않았다.
- **그 밖의 미구현 항목:** LLM 대화, 자동 119 신고, 미저장 초안의 영구 복원. 이 문서에서 새 개발 계획으로 확정하지 않았다.

실제 마이크·한국어 음성 출력의 환경별 검증 범위는 [STT/TTS 보고서](SPEECH_INPUT_REPORT.md)를 따른다.

## 4. 코드와 단계 대응

| 구현 단계 | 실제 파일·함수 |
|---|---|
| 수신/거절·종료 화면 | [CallPage.jsx](../frontend/src/pages/CallPage.jsx), [IncomingCall.jsx](../frontend/src/components/IncomingCall.jsx), [CallControls.jsx](../frontend/src/components/CallControls.jsx) |
| 벨소리·해제 | [useRingtone.js](../frontend/src/hooks/useRingtone.js) — useRingtone |
| 시작·복원·답변 전송·종료 요청 | [useCall.js](../frontend/src/hooks/useCall.js) — load, begin, decline, submitAnswer, finish, saveFinish. [api.js](../frontend/src/api.js) — HTTP 오류·시간 제한 |
| 질문·후속 응답 TTS | [synthesis.js](../frontend/src/speech/synthesis.js) — SpeechOutput.speak/stop/dispose |
| STT·실패 대체 | [recognition.js](../frontend/src/speech/recognition.js) — SpeechInput.start/stop/dispose |
| 텍스트·현재 질문·인식 표시 | [TextAnswerInput.jsx](../frontend/src/components/TextAnswerInput.jsx), [ConversationPanel.jsx](../frontend/src/components/ConversationPanel.jsx), [SpeechInputStatus.jsx](../frontend/src/components/SpeechInputStatus.jsx) |
| 요청 검증·DB 저장/조회·중복 | [main.py](../backend/main.py) — TurnInput, start_call, decline_call, add_turn, finish_call, calls, call_detail, db |
| 규칙 판정·후속 응답·요약 | [conversation.py](../backend/conversation.py) — QUESTIONS, assess, urgent, summary_for |
| 생활지원사 기록 조회/상세 | [RecordsPage.jsx](../frontend/src/pages/RecordsPage.jsx) — 목록 조회 및 상세 모달 |

## 5. Mermaid 검사 및 SVG

두 Mermaid 코드 블록은 동일한 소스로 파싱·SVG 렌더링하여 문법을 검사한다. SVG에서는 HTML foreignObject 대신 텍스트 라벨을 사용한다. 검사 결과·Mermaid 버전은 [검증 기록](verification/conversation-flow-validation.json)에 저장한다. 문서 링크와 SVG의 XML 구조도 함께 확인한다. 이번 변경은 문서·이미지뿐이며 앱 동작을 변경하지 않는다.

## 짧은 답변·기록·복구 수정 (2026-11-13)

짧은 응/어는 직전 질문이 단일 확인형일 때만 해석한다. 열린 질문이나 양자택일에는 임의로 긍정 값을 넣지 않는다. 잤어는 수면 사실/수면의 질 미확인으로 구분한다. 재질문은 단일 질문이며, 실제 출력 질문을 서버 이력에 보존한다.

입력은 sessionStorage에 통화·문항·시도별로 보관한다. 새로고침 시 같은 순번이면 복원하고, 이미 서버에 저장된 답변이면 중복 전송하지 않는다. 409는 서버 상세를 다시 조회한다. 이전 문항의 다른 초안은 별도 표시하고 새 질문에 자동으로 전송하지 않는다. 명시적 통화 종료 시 초안을 정리한다. 전화 예약 경로와 스케줄러는 제거했으며 일반 수신 체험과 기존 저장 흐름은 유지한다. 상세 검증은 [이번 보고서](CALL_REPAIR_REPORT.md)를 참고한다.
