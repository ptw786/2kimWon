# 안심온 API 계약 v2.1

> v2.1 (2026-11-14): 단계 라벨을 팀 용어로 통일, 어려움 유형(`needs`) 추가, 복지서비스 연계(`welfare`) 추가. 키(grade 값)는 그대로라 기존 코드는 라벨만 바뀐다.

웹(`apps/web`)·앱(`apps/app`)·서버(`apps/api`)가 지키는 약속. 바꿀 때는 이 파일을 먼저 고친다.

- 기본 주소: `/api` (개발 중엔 Vite가 `http://127.0.0.1:8010`으로 넘긴다)
- 시각: ISO 8601, 한국 시간(`+09:00`). "오늘"은 한국 시간 자정 기준.
- 오류: `{ "detail": "<사용자에게 보여줄 수 있는 한국어 문장>" }` + 4xx/5xx
- 항목 키(topic): `body`(몸 상태) · `meal`(식사) · `sleep`(수면) · `med`(복약) · `mood`(기분) — 질문 순서도 이 순서
- 항목 상태: `good`(양호) · `caution`(주의) · `risk`(위험) · `unknown`(미확인)
- 단계(grade): `urgent`(즉시 확인) · `today`(우선 확인) · `watch`(추가 확인) · `ok`(특이 표현 없음) — 키는 v2 그대로, 라벨만 바뀜
- 어려움 유형(need): `meal_difficulty`(식사 어려움) · `sleep_problem`(수면 문제) · `help_request`(도움 요청) · `loneliness`(외로움)
- 통화 상태: `ringing` · `in_progress` · `completed` · `interrupted` · `missed` · `declined`

## 공통 객체

```ts
type Assessment = {
  score: number                 // 0~100
  grade: 'urgent'|'today'|'watch'|'ok'
  grade_label: string           // '즉시 확인' | '우선 확인' | '추가 확인' | '특이 표현 없음'
  reasons: { kind: 'safety'|'item'|'trend'|'contact', chip: string, points: number, quote: string|null }[]
  items: Record<Topic, { status: ItemStatus, quote: string|null, origin: 'llm'|'rule'|'none' }>
  safety: { category: string, quote: string }[]
  needs_check: Topic[]          // 미확인 항목
  needs: Need[]                 // 어려움 유형 (점수와 별개, 복지서비스 연계의 입력)
  rule_version: string          // 'r2'
}

type CallSummary = {
  id: number, resident_id: number, resident_name: string,
  status: CallStatus, status_label: string,     // '통화 완료' 등
  created_at: string, started_at: string|null, ended_at: string|null,
  summary: string|null,                          // 통화 요약 (완료·중단 후)
  assessment: Assessment|null                    // 통화가 끝난 뒤 계산
}

type Turn = {
  role: 'ai'|'elder', text: string, topic: Topic|null, at: string,
  source?: 'stt'|'text'|'option'|'silence',
  judged?: { topic: Topic, status: ItemStatus, origin: 'llm'|'rule' }[]   // elder 턴에만: 이 답변으로 판정된 항목
  needs?: Need[]                                                          // elder 턴에만: 이 답변에서 찾은 어려움
  ms?: number|null                                                        // ai 턴에만: 이 응답을 만드는 데 든 AI 시간 합(추출+공감), 규칙만 썼으면 null
}

type Need = { type: 'meal_difficulty'|'sleep_problem'|'help_request'|'loneliness', label: string, quote: string, origin: 'llm'|'rule' }

type WelfareMatch = {
  need: Need['type'], need_label: string,
  region: string,                  // 검색한 지역 '서울특별시 서대문구'
  services: {
    id: string, name: string,        // servId · servNm
    org: string|null,                // 담당 부서·기관
    area: string,                    // '서울특별시 서대문구' 또는 '전국(중앙부처)'
    summary: string|null,            // servDgst
    target_quote: string|null,       // 지원대상 원문 일부 (상세가 없으면 null)
    apply_quote: string|null,        // 신청방법 원문 일부
    link: string|null,               // 복지로 상세 주소
    source: '지자체복지서비스'|'중앙부처복지서비스',
  }[],                               // 최대 3건, 0건 허용
  note: string|null,                 // '이 지역에는 해당 사업이 없어 중앙부처 서비스를 보여 드려요' 등
  data_as_of: string                 // 데이터 조회일 'YYYY-MM-DD'
}

type AiRun = {                     // 통화 상세·실시간 화면의 'AI 실행 기록'
  at: string,
  step: 'extract'|'empathy'|'summary',
  model: string|null,              // 'ax4-light:q4_K_M' 등, 규칙만 썼으면 null
  ms: number|null,
  outcome: 'ok'|'fallback',        // fallback = 시간 초과·형식 오류·연결 실패로 규칙이 대신함
  note: string|null                // '시간 초과 4.0s' 등
}
```

- 어르신 코드(`code`): `KY-01` 같은 짧은 코드. 웹 QR은 `${APP_PUBLIC_URL}/r/${code}`를 담고, 앱은 이 코드로 어르신을 찾는다.

## 시스템

| 메서드 | 경로 | 응답 |
|---|---|---|
| GET | `/api/health` | `{ ok: true, db: true, llm: { mode: 'ollama'|'rules', model: string|null, reachable: boolean } }` |

## 생활지원사 웹 (`/api/staff`)

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/staff/dashboard` | – | `{ date, counts: { total, urgent, today, watch, ok, missed, not_called }, residents: ResidentRow[] }` 단계 → 점수 높은 순 |
| GET | `/staff/residents/{id}` | – | `{ resident, week: Day[7], calls: CallSummary[], welfare: WelfareMatch[] }` week는 오래된 날 → 오늘. welfare는 최근 7일 needs 기준 |
| POST | `/staff/residents` | `{ name, age, region, neighborhood, call_time:'HH:MM', memo? }` | 201 `Resident` |
| PATCH | `/staff/residents/{id}` | 위 필드 일부 | `Resident` |
| POST | `/staff/residents/{id}/call` | – | 201 `CallSummary`(ringing). 이미 벨이 울리거나 통화 중이면 409 |
| GET | `/staff/calls` | `?date=YYYY-MM-DD&resident_id=&limit=50` | `CallSummary[]` 최신순 |
| GET | `/staff/calls/{id}` | – | `CallSummary & { turns: Turn[], ai_runs: AiRun[], staff_check, step: { index, total: 5 }, welfare: WelfareMatch[] }` 실시간 화면도 이걸 2초마다 호출 |
| GET | `/staff/live` | – | `{ calls: (CallSummary & { step })[] }` 지금 `ringing`·`in_progress`인 통화 |
| POST | `/staff/demo/reset` | – | `{ ok: true }` 시드 데이터로 되돌림 (시연용, `ANSIMON_DEMO=1`일 때만) |
| POST | `/staff/calls/{id}/check` | `{ note: string }` (0~300자) | `{ checked: true, note, at }` 생활지원사 확인 기록 |

```ts
type Resident = { id, code, name, age, region: string, neighborhood, call_time, memo: string|null, is_virtual: boolean }   // region = '대전광역시 중구' 처럼 시도+시군구 (복지서비스 검색용)
type ResidentRow = Resident & {
  today: { call_id: number|null, status: CallStatus|'not_called', status_label: string },
  assessment: Assessment|null,          // 오늘 마지막으로 끝난 통화 기준 (추세·미응답 포함)
  staff_check: { checked: boolean, note: string, at: string }|null
}
type Day = { date: string, call_status: CallStatus|'not_called', items: Record<Topic, ItemStatus>|null, grade: Grade|null, score: number|null }
```

## 어르신 앱 (`/api/elder`)

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/elder/residents` | – | `{ id, code, name }[]` — 시연용: 앱 처음 켤 때 누구 폰인지 고름 |
| GET | `/elder/by-code/{code}` | – | `{ id, code, name }` 없으면 404 (QR로 열었을 때) |
| GET | `/elder/{residentId}/home` | – | `{ name, call_time, today: { status, status_label }, yesterday_label, week_count }` 홈 화면 |
| GET | `/elder/{residentId}/records` | – | `{ date, time: string|null, minutes: number|null, status_label, chips: { label, tone: 'ok'|'watch' }[] }[]` 최근 14일, 쉬운 말 |
| GET | `/elder/{residentId}/incoming` | – | `{ ringing: { call_id, ring_expires_at }|null, active: { call_id }|null }` 앱이 2초마다 호출 |
| POST | `/elder/calls/{id}/answer` | – | `TurnResult` (인사 + 첫 질문) |
| POST | `/elder/calls/{id}/decline` | – | `{ status: 'declined' }` |
| POST | `/elder/calls/{id}/turn` | `{ text: string(0~500), source: 'stt'|'text'|'option'|'silence', client_turn_id: string }` | `TurnResult` |
| POST | `/elder/calls/{id}/hangup` | – | `{ status }` 마지막 질문 전이면 interrupted |
| GET | `/elder/calls/{id}` | – | `{ status, step, question, turns: Turn[] }` 새로고침 후 이어가기 |

```ts
type TurnResult = {
  ai_text: string            // TTS로 읽을 전체 문장 (공감 + 다음 질문, 또는 마무리 인사)
  empathy: string|null       // 공감 문장만
  question: string|null      // 다음 질문 원문 (끝났으면 null)
  topic: Topic|null
  options: string[]          // 큰 선택 버튼 문구 (예: 식사 → ['네, 먹었어요','조금 먹었어요','못 먹었어요']). 누르면 source:'option'으로 그 문구를 보냄
  step: { index: number, total: 5 }   // index = 지금 묻는 질문 번호(1부터)
  action: 'start'|'next'|'repeat'|'reask'|'safety'|'finish'
  safety: boolean            // 이번 답변에서 안전 신호 감지
  finished: boolean          // true면 앱은 마무리 인사를 읽은 뒤 종료 화면
  llm_used: boolean          // 이번 응답에 Ollama를 썼는지 (시연·평가용)
}
```

- `client_turn_id`가 같은 요청이 다시 오면 저장하지 않고 처음 결과를 그대로 돌려준다(새로고침·재전송 대비).
- `source: 'silence'`는 앱이 10초 동안 아무 말도 못 들었을 때 보낸다(`text`는 빈 문자열).
