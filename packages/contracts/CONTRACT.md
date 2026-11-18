# 안심온 API 계약 v3

> v3 (2026-11-16, 외부 리뷰·QA 반영): 단계 규칙 r3(사실로 단계·`grade_basis`), 통화 중 안전 신호 판정(`provisional`)·`/staff/alerts`, 대시보드 대표 판정(`assessment_call_id`), 생활지원사 로그인(`/staff/login`, `Authorization: Bearer`), 어르신 '지금 전화 받기'(`/elder/{id}/ring`), 턴의 `topic`(412), 이어 받기 응답 확장, 기록 칩 `unknown`.
> F11 통합(2026-11-18): 복지 후보는 내용 해시가 검토 기록과 일치하는 사업만 반환한다.
> 아래 부가 필드는 웹에서 표시하고 앱은 복지 API를 사용하지 않는다. 위험 점수 계약은 그대로다.

## F11 부가 계약

- `WelfareService` 추가: `eligibility: {status:'needs_check', reasons:string[]}`, `checked_at:string|null`,
  `contact:string|null`, `missing_fields:string[]`, `target_text:string|null`, `criteria_text:string|null`,
  `apply_text:string|null`, `review_note:string`, `source_area:string`.
- `checked_at`은 해당 사업 상세를 조회한 날짜다. 파일 갱신일과 구분하며, 선정 확정을 뜻하지 않는다.
- 나이는 신청 자격에만 사용한다. 소득·가구·장애·중복수혜 등 알 수 없는 조건을 추측하지 않는다.
- `GET /staff/public-data`: `{catalog:{total,reviewed,pending,excluded,unavailable}, statistics:{source,year,source_file,regions:KosisRegion[]}}`.
  KosisRegion은 원본 `region,level,elderly_single_households,all_households,ratio_percent`와
  `normalized_region:string`, `aggregation_level:'national'|'province'|'district'|'subdistrict'`를 포함한다.
- 원본 지역명은 보존한다. 제공 KOSIS의 계층으로 만든 대응표에 없는 모호한 지역은 추천하지 않는다.
- KOSIS 통계는 지역 규모 비교용이며 개인 판정·지원 자격에 사용하지 않는다. 서로 다른 계층은 합산하지 않는다.

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
  needs: Need[]                 // 어려움 유형 (점수와 별개, 복지서비스 연계의 입력). 있으면 단계는 최소 '추가 확인'
  grade_basis: string|null      // 이 단계인 이유 한 줄 ('위험 항목 (몸 상태)', '연속 미응답 2회' …). r3 이전 기록은 null
  provisional: boolean          // true = 통화 중 안전 신호로 미리 만든 판정 (통화가 끝나면 최종 판정으로 바뀜)
  rule_version: string          // 'r3'
}

type CallSummary = {
  id: number, resident_id: number, resident_name: string,
  status: CallStatus, status_label: string,     // '통화 완료' 등
  created_at: string, started_at: string|null, ended_at: string|null,
  summary: string|null,                          // 통화 요약 (완료·중단 후)
  assessment: Assessment|null                    // 통화가 끝난 뒤 계산. 통화 중 안전 신호가 나오면 그때 provisional 판정
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
| GET | `/api/health` | `{ ok: true, db: true, llm: { mode: 'ollama'|'rules', model: string|null, reachable: boolean }, auth: { required: boolean }, demo: boolean }` |

## 생활지원사 웹 (`/api/staff`)

`/staff/login`을 뺀 모든 요청은 `Authorization: Bearer <token>`이 필요하다(없거나 틀리면 401). 토큰은 PIN으로 받는다. PIN은 `ANSIMON_STAFF_PIN`, 없으면 서버가 켤 때 6자리를 만들어 로그에 보여 준다. `ANSIMON_STAFF_PIN=off`는 자동 테스트용.

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| POST | `/staff/login` | `{ pin }` | `{ token, required }` 틀리면 401, 5분에 5번 넘게 틀리면 429 |
| GET | `/staff/alerts` | – | `{ alerts: { id, call_id, resident_id, resident_name, code, category, quote, at, live }[] }` 오늘 안전 신호 중 확인 기록이 없는(또는 확인 뒤에 새로 나온) 것, 최신순. `live` = 통화 중 |
| GET | `/staff/dashboard` | – | `{ date, counts: { total, urgent, today, watch, ok, missed, not_called }, residents: ResidentRow[] }` 단계 → 점수 높은 순 |
| GET | `/staff/residents/{id}` | – | `{ resident, week: Day[7], calls: CallSummary[], welfare: WelfareMatch[] }` week는 오래된 날 → 오늘. welfare는 최근 7일 needs 기준 |
| POST | `/staff/residents` | `{ name, age, region, neighborhood, call_time:'HH:MM', memo? }` | 201 `Resident` |
| PATCH | `/staff/residents/{id}` | 위 필드 일부 | `Resident` |
| POST | `/staff/residents/{id}/call` | – | 201 `CallSummary`(ringing). 이미 벨이 울리거나 통화 중이면 409 |
| GET | `/staff/calls` | `?date=YYYY-MM-DD&resident_id=&limit=50` | `CallSummary[]` 최신순 |
| GET | `/staff/calls/{id}` | – | `CallSummary & { turns: Turn[], ai_runs: AiRun[], staff_check, step: { index, total: 5 }, welfare: WelfareMatch[] }` 실시간 화면도 이걸 2초마다 호출 |
| GET | `/staff/live` | – | `{ calls: (CallSummary & { step })[] }` 지금 `ringing`·`in_progress`인 통화 |
| POST | `/staff/demo/reset` | – | `{ ok: true }` 시드 데이터로 되돌림 (시연용, `ANSIMON_DEMO=1`일 때만 — 기본은 꺼짐, `scripts/dev-up.sh`가 켬) |
| POST | `/staff/calls/{id}/check` | `{ note: string }` (0~300자) | `{ checked: true, note, at }` 생활지원사 확인 기록 |

```ts
type Resident = { id, code, name, age, region: string, neighborhood, call_time, memo: string|null, is_virtual: boolean }   // region = '대전광역시 중구' 처럼 시도+시군구 (복지서비스 검색용)
type ResidentRow = Resident & {
  today: { call_id: number|null, status: CallStatus|'not_called', status_label: string, calls: number },   // 오늘 마지막 통화
  assessment: Assessment|null,          // 오늘의 대표 판정 = 오늘 통화 중 **가장 심한** 것 (같은 단계면 확인 안 한 것 → 점수 → 최근). 통화 중 안전 신호 포함
  assessment_call_id: number|null,      // 대표 판정을 만든 통화 (확인 기록·상세는 이 통화로)
  staff_check: { checked: boolean, note: string, at: string }|null   // assessment_call_id 통화의 확인 기록만
}
type Day = { date: string, call_status: CallStatus|'not_called', items: Record<Topic, ItemStatus>|null, grade: Grade|null, score: number|null }
```

## 어르신 앱 (`/api/elder`)

| 메서드 | 경로 | 요청 | 응답 |
|---|---|---|---|
| GET | `/elder/residents` | – | `{ id, code, name }[]` — 시연 모드에서만(아니면 403). 실제로는 QR·코드로만 연다 |
| POST | `/elder/{residentId}/ring` | – | 201 `{ call_id }` 어르신이 '지금 전화 받기'를 누름. 이미 울리거나 통화 중이면 409 |
| GET | `/elder/by-code/{code}` | – | `{ id, code, name }` 없으면 404 (QR로 열었을 때) |
| GET | `/elder/{residentId}/home` | – | `{ name, call_time, today: { status, status_label }, yesterday_label, week_count }` 홈 화면 |
| GET | `/elder/{residentId}/records` | – | `{ date, time: string|null, minutes: number|null, status_label, chips: { label, tone: 'ok'|'watch'|'unknown' }[] }[]` 최근 14일, 쉬운 말 |
| GET | `/elder/{residentId}/incoming` | – | `{ ringing: { call_id, ring_expires_at }|null, active: { call_id }|null }` 앱이 2초마다 호출 |
| POST | `/elder/calls/{id}/answer` | – | `TurnResult` (인사 + 첫 질문) |
| POST | `/elder/calls/{id}/decline` | – | `{ status: 'declined' }` |
| POST | `/elder/calls/{id}/turn` | `{ text: string(0~500), source: 'stt'|'text'|'option'|'silence', client_turn_id: string, topic?: Topic }` | `TurnResult`. `topic`(앱이 보고 있던 질문)이 서버의 지금 질문과 다르면 412 → 앱은 `GET /elder/calls/{id}`로 다시 맞춘다 |
| POST | `/elder/calls/{id}/hangup` | – | `{ status }` 마지막 질문 전이면 interrupted |
| GET | `/elder/calls/{id}` | – | `{ status, step, question, topic, options, last_ai_text, turns: Turn[] }` 새로고침 후 이어가기. 마지막으로 보낸 질문·선택지 그대로(식사 재질문 포함) |

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
- 다섯 질문 동안 조용함만 있었으면 통화는 `interrupted`로 닫히고 판정 이유에 '받았지만 대답 없음'(+10)이 붙는다.
- 안전 신호 턴의 `ai_text`는 '생활지원사님 화면에 바로 알렸어요. 위급하시면 지금 119에 전화하세요.'(자해·삶의 의지면 109 안내를 덧붙임).

## 2026-11-18 통합 보완

- `GET /staff/calls`에 `offset`(0 이상), `grade`(`urgent|today|watch|ok|none`, 생략 시 전체)를 추가한다.
  단계 필터는 페이지를 자르기 전에 적용한다. 응답 배열·기본 limit=50·최대 limit=200은 유지한다.
- `health.llm.reachable`은 Ollama 서버 응답과 지정 모델 설치 여부를 모두 확인한다.
- 안전 신호·주의/위험/미확인·생활 어려움·중단이 있는 통화는 확정 사실의 규칙 요약을 유지한다.
  AI 요약을 거절한 이유는 `ai_runs`에 남긴다. 문제 없는 완료 통화의 AI 요약은 기존과 같다.
