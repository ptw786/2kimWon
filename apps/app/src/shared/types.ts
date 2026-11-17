// packages/contracts/CONTRACT.md 의 어르신 앱(/api/elder) 부분만 옮겼다. 계약이 바뀌면 여기도 고친다.

export type Topic = 'body' | 'meal' | 'sleep' | 'med' | 'mood'
export type CallStatus = 'ringing' | 'in_progress' | 'completed' | 'interrupted' | 'missed' | 'declined'
export type TurnSource = 'stt' | 'text' | 'option' | 'silence'

export type ResidentRef = { id: number; code: string; name: string }

export type HomeData = {
  name: string
  call_time: string // 'HH:MM'
  today: { status: CallStatus | 'not_called'; status_label: string }
  yesterday_label: string
  week_count: number
}

export type RecordDay = {
  date: string // 'YYYY-MM-DD'
  time: string | null
  minutes: number | null
  status_label: string
  chips: { label: string; tone: 'ok' | 'watch' }[]
}

export type Incoming = {
  ringing: { call_id: number; ring_expires_at: string } | null
  active: { call_id: number } | null
}

export type Step = { index: number; total: number }

export type TurnResult = {
  ai_text: string
  empathy: string | null
  question: string | null
  topic: Topic | null
  options: string[]
  step: Step
  action: 'start' | 'next' | 'repeat' | 'reask' | 'safety' | 'finish'
  safety: boolean
  finished: boolean
  llm_used: boolean
}

export type TurnRequest = { text: string; source: TurnSource; client_turn_id: string }

export type Turn = { role: 'ai' | 'elder'; text: string; topic: Topic | null; at: string; source?: TurnSource }

export type CallState = { status: CallStatus; step: Step; question: string | null; turns: Turn[] }

export interface ElderApi {
  residents(): Promise<ResidentRef[]>
  byCode(code: string): Promise<ResidentRef>
  home(residentId: number): Promise<HomeData>
  records(residentId: number): Promise<RecordDay[]>
  incoming(residentId: number): Promise<Incoming>
  answer(callId: number): Promise<TurnResult>
  decline(callId: number): Promise<{ status: string }>
  turn(callId: number, body: TurnRequest): Promise<TurnResult>
  hangup(callId: number): Promise<{ status: string }>
  call(callId: number): Promise<CallState>
  /** 시연용: 생활지원사 웹의 '전화 걸기'와 같은 요청(POST /api/staff/residents/{id}/call). */
  ringMe(residentId: number): Promise<void>
}
