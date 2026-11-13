// VITE_MOCK=1 일 때 쓰는 가짜 어르신 API. 서버 없이 화면을 만들고 찍기 위한 대본이다.
// 벨 → 다섯 질문(몸·식사·수면·약·기분) → 마무리 인사를 계약(TurnResult) 모양 그대로 흉내 낸다.
import { ApiError } from '../shared/errors.ts'
import type { CallState, CallStatus, ElderApi, HomeData, Incoming, RecordDay, ResidentRef, Topic, Turn, TurnRequest, TurnResult } from '../shared/types.ts'

const RESIDENTS: ResidentRef[] = [
  { id: 1, code: 'KY-01', name: '김영자' },
  { id: 2, code: 'PS-02', name: '박순자' },
  { id: 3, code: 'LM-03', name: '이말순' },
]

const QUESTIONS: { topic: Topic; question: string; options: string[]; chipOk: string; chipWatch: string }[] = [
  { topic: 'body', question: '오늘 몸은 좀 어떠세요?', options: ['괜찮아요', '조금 불편해요', '많이 아파요'], chipOk: '몸 괜찮음', chipWatch: '몸 불편' },
  { topic: 'meal', question: '오늘 아침 식사는 하셨어요?', options: ['네, 먹었어요', '조금 먹었어요', '못 먹었어요'], chipOk: '식사 잘함', chipWatch: '식사 걱정' },
  { topic: 'sleep', question: '어젯밤 잠은 잘 주무셨어요?', options: ['잘 잤어요', '조금 설쳤어요', '거의 못 잤어요'], chipOk: '잘 주무심', chipWatch: '잠 설침' },
  { topic: 'med', question: '드시는 약은 오늘 챙겨 드셨어요?', options: ['네, 먹었어요', '아직 못 먹었어요', '먹는 약 없어요'], chipOk: '약 챙김', chipWatch: '약 걱정' },
  { topic: 'mood', question: '요즘 기분은 어떠세요?', options: ['좋아요', '그저 그래요', '우울해요'], chipOk: '기분 좋음', chipWatch: '기분 걱정' },
]

const NEGATIVE = /(못|안 ?먹|아파|아프|불편|설쳤|우울|걸렀|없어|그저|힘들|외로|아직)/
const SAFETY = /(쓰러|넘어졌|숨이|가슴이|죽고|119)/
const REPEAT = /(다시|뭐라고|못 들었|잘 안 들려)/

type MockCall = {
  id: number
  residentId: number
  status: CallStatus
  ringExpires: number
  index: number // 0-based question index
  reasks: number
  watch: boolean[]
  turns: Turn[]
  replies: Map<string, TurnResult>
  startedAt: number
}

let nextId = 231
const calls = new Map<number, MockCall>()
const delay = (ms = 350) => new Promise((r) => setTimeout(r, ms))

// 시험 스크립트(scripts/*.py)가 어떤 요청이 어떤 순서로 갔는지 확인할 수 있게 남긴다.
type MockLog = { at: number; req: string; body?: unknown }[]
function log(req: string, body?: unknown) {
  const w = globalThis as unknown as { __ansimonMockLog?: MockLog }
  ;(w.__ansimonMockLog ??= []).push({ at: Date.now(), req, body })
}

function ringMs(): number {
  try { const v = Number(sessionStorage.getItem('ansimon.mock.ringMs')); if (v > 0) return v } catch { /* ignore */ }
  return 30000
}

function kstDate(offsetDays = 0): string {
  const kst = new Date(Date.now() + 9 * 3600_000 + offsetDays * 86400_000)
  return kst.toISOString().slice(0, 10)
}
const nowIso = () => new Date().toISOString()

function resident(id: number): ResidentRef {
  const r = RESIDENTS.find((x) => x.id === id)
  if (!r) throw new ApiError(404, '어르신을 찾지 못했어요.')
  return r
}

function todayCall(residentId: number): MockCall | undefined {
  return [...calls.values()].reverse().find((c) => c.residentId === residentId)
}

function expire(c: MockCall) {
  if (c.status === 'ringing' && Date.now() > c.ringExpires) c.status = 'missed'
}

function result(c: MockCall, ai_text: string, empathy: string | null, action: TurnResult['action'], safety = false): TurnResult {
  const q = QUESTIONS[c.index]
  const finished = action === 'finish'
  return {
    ai_text, empathy,
    question: finished ? null : q.question,
    topic: finished ? null : q.topic,
    options: finished ? [] : q.options,
    step: { index: Math.min(c.index + 1, 5), total: 5 },
    action, safety, finished, llm_used: false,
  }
}

function aiSay(c: MockCall, r: TurnResult): TurnResult {
  c.turns.push({ role: 'ai', text: r.ai_text, topic: r.topic, at: nowIso() })
  return r
}

function getCall(id: number): MockCall {
  const c = calls.get(id)
  if (!c) throw new ApiError(404, '통화를 찾지 못했어요.')
  expire(c)
  return c
}

export const mockApi: ElderApi = {
  async residents() { await delay(200); return RESIDENTS },
  async byCode(code) {
    await delay(200)
    const r = RESIDENTS.find((x) => x.code.toLowerCase() === code.toLowerCase())
    if (!r) throw new ApiError(404, '이 코드의 어르신을 찾지 못했어요.')
    return r
  },
  async home(id): Promise<HomeData> {
    await delay(200)
    const r = resident(id)
    const c = todayCall(id)
    const status = c ? c.status : 'not_called'
    const label: Record<string, string> = { not_called: '아직 전화 전이에요', completed: '통화 완료', interrupted: '중간에 끊겼어요', missed: '못 받으셨어요', declined: '안 받으셨어요', ringing: '벨이 울려요', in_progress: '통화 중' }
    return { name: r.name, call_time: '10:00', today: { status, status_label: label[status] }, yesterday_label: '받으심', week_count: 5 }
  },
  async records(id): Promise<RecordDay[]> {
    await delay(250)
    resident(id)
    const days: RecordDay[] = []
    const c = todayCall(id)
    if (c && (c.status === 'completed' || c.status === 'interrupted')) {
      const start = new Date(c.startedAt + 9 * 3600_000)
      const chips = c.watch.map((w, i) => ({ label: w ? QUESTIONS[i].chipWatch : QUESTIONS[i].chipOk, tone: (w ? 'watch' : 'ok') as 'ok' | 'watch' }))
      days.push({ date: kstDate(0), time: start.toISOString().slice(11, 16), minutes: Math.max(1, Math.round((Date.now() - c.startedAt) / 60000)), status_label: c.status === 'completed' ? '통화 완료' : '중간에 끊겼어요', chips })
    } else {
      days.push({ date: kstDate(0), time: '10:31', minutes: 3, status_label: '통화 완료', chips: [{ label: '식사 걱정', tone: 'watch' }, { label: '잠 설침', tone: 'watch' }, { label: '몸 괜찮음', tone: 'ok' }] })
    }
    days.push({ date: kstDate(-1), time: null, minutes: null, status_label: '전화를 못 받으셨어요', chips: [] })
    days.push({ date: kstDate(-2), time: '10:02', minutes: 2, status_label: '통화 완료', chips: [{ label: '식사 잘함', tone: 'ok' }, { label: '잘 주무심', tone: 'ok' }] })
    days.push({ date: kstDate(-3), time: '10:05', minutes: 3, status_label: '통화 완료', chips: [{ label: '몸 괜찮음', tone: 'ok' }, { label: '기분 좋음', tone: 'ok' }] })
    return days
  },
  async incoming(id): Promise<Incoming> {
    await delay(120)
    const c = todayCall(id)
    if (c) expire(c)
    return {
      ringing: c && c.status === 'ringing' ? { call_id: c.id, ring_expires_at: new Date(c.ringExpires).toISOString() } : null,
      active: c && c.status === 'in_progress' ? { call_id: c.id } : null,
    }
  },
  async ringMe(id) {
    log(`POST /staff/residents/${id}/call`)
    await delay(200)
    resident(id)
    const c = todayCall(id)
    if (c) expire(c)
    if (c && (c.status === 'ringing' || c.status === 'in_progress')) throw new ApiError(409, '이미 벨이 울리거나 통화 중이에요.')
    const call: MockCall = { id: nextId++, residentId: id, status: 'ringing', ringExpires: Date.now() + ringMs(), index: 0, reasks: 0, watch: [], turns: [], replies: new Map(), startedAt: Date.now() }
    calls.set(call.id, call)
  },
  async answer(callId) {
    log(`POST /elder/calls/${callId}/answer`)
    await delay()
    const c = getCall(callId)
    if (c.status !== 'ringing') throw new ApiError(409, '이미 끝난 전화예요.')
    c.status = 'in_progress'
    c.startedAt = Date.now()
    const name = resident(c.residentId).name
    return aiSay(c, result(c, `${name} 어르신, 안녕하세요. 안심온이에요. ${QUESTIONS[0].question}`, null, 'start'))
  },
  async decline(callId) {
    log(`POST /elder/calls/${callId}/decline`)
    await delay(200)
    const c = getCall(callId)
    c.status = 'declined'
    return { status: 'declined' }
  },
  async turn(callId, body: TurnRequest) {
    log(`POST /elder/calls/${callId}/turn`, body)
    await delay(450)
    const c = getCall(callId)
    const seen = c.replies.get(body.client_turn_id)
    if (seen) return seen
    if (c.status !== 'in_progress') throw new ApiError(409, '이미 끝난 전화예요.')
    const text = body.text.trim()
    c.turns.push({ role: 'elder', text, topic: QUESTIONS[c.index].topic, at: nowIso(), source: body.source })
    let r: TurnResult
    if (body.source === 'silence' || !text) {
      if (c.reasks < 1) {
        c.reasks++
        r = result(c, `잘 못 들었어요. 천천히 다시 말씀해 주세요. ${QUESTIONS[c.index].question}`, null, 'reask')
      } else {
        r = advance(c, '괜찮아요, 다음에 다시 여쭐게요.', true)
      }
    } else if (REPEAT.test(text)) {
      r = result(c, `다시 여쭐게요. ${QUESTIONS[c.index].question}`, null, 'repeat')
    } else if (SAFETY.test(text)) {
      r = advance(c, '많이 놀라셨겠어요. 생활지원사님께 바로 알려 드릴게요.', true, true)
    } else {
      const negative = NEGATIVE.test(text)
      r = advance(c, negative ? '그러셨군요. 마음이 쓰이네요.' : '다행이에요.', negative)
    }
    aiSay(c, r)
    c.replies.set(body.client_turn_id, r)
    return r
  },
  async hangup(callId) {
    log(`POST /elder/calls/${callId}/hangup`)
    await delay(200)
    const c = getCall(callId)
    if (c.status === 'in_progress') c.status = c.index >= 5 ? 'completed' : 'interrupted'
    return { status: c.status }
  },
  async call(callId): Promise<CallState> {
    await delay(200)
    const c = getCall(callId)
    const q = QUESTIONS[Math.min(c.index, 4)]
    return { status: c.status, step: { index: Math.min(c.index + 1, 5), total: 5 }, question: c.status === 'in_progress' ? q.question : null, turns: c.turns }
  },
}

function advance(c: MockCall, empathy: string, watch: boolean, safety = false): TurnResult {
  c.watch[c.index] = watch
  c.reasks = 0
  c.index++
  if (c.index >= QUESTIONS.length) {
    c.status = 'completed'
    return result(c, `${empathy} 오늘도 이야기 나눠 주셔서 고맙습니다. 내일 오전 10시에 다시 전화드릴게요. 건강하세요.`, empathy, 'finish', safety)
  }
  return result(c, `${empathy} ${QUESTIONS[c.index].question}`, empathy, safety ? 'safety' : 'next', safety)
}
