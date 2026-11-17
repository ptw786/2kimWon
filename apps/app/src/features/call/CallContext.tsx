// 전화 한 통의 흐름을 맡는다: 벨 확인(2초마다) → 받기 → [읽기(TTS) → 듣기(STT) → 답 보내기] 반복 → 마무리.
// 원칙: 마이크와 읽기는 절대 동시에 켜지지 않는다. 네트워크가 끊겨도 쓴 답은 지우지 않고 같은 client_turn_id로 다시 보낸다.
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, ApiError, friendly, newTurnId } from '../../shared/api.ts'
import { useSettings } from '../../shared/settings.tsx'
import { MIC_UNAVAILABLE, SpeechInput, type RecognitionHost, type SttState } from './speech/recognition.ts'
import { SpeechOutput, type SynthesisHost } from './speech/synthesis.ts'
import type { Incoming, TurnRequest, TurnResult, TurnSource } from '../../shared/types.ts'

export type Phase = 'idle' | 'ringing' | 'answering' | 'talk' | 'done'
export type Voice = 'speaking' | 'starting' | 'listening' | 'idle' | 'sending'
export type Heard = { text: string; kind: 'interim' | 'stt' | 'option' | 'text' } | null
export type MicProblem = { message: string; code: string } | null

const SILENCE_MS = 10_000
const POLL_MS = 2_000
export const MISSED_NOTICE = '전화를 못 받으셨어요. 다음 전화를 기다려 주세요.'
const ENDED_NOTICE = '전화를 끊었어요. 다음 전화 때 다시 여쭐게요.'

type CallCtx = {
  phase: Phase
  callId: number | null
  result: TurnResult | null
  voice: Voice
  heard: Heard
  selected: string | null
  micProblem: MicProblem
  sttHint: string
  ttsNotice: string
  error: string | null
  draft: string
  textOpen: boolean
  notice: string | null
  ringError: string | null
  homeVersion: number
  setDraft: (text: string) => void
  setTextOpen: (open: boolean) => void
  ringMe: () => Promise<void>
  answer: () => void
  decline: () => void
  choose: (option: string) => void
  sendText: () => void
  toggleMic: () => void
  retryMic: () => void
  retry: () => void
  hold: (on: boolean) => void
  hangup: () => Promise<void>
  finish: () => void
  dismissNotice: () => void
}

const Ctx = createContext<CallCtx | null>(null)

function unlockSpeech() {
  // iOS·안드로이드 크롬은 사용자가 누른 순간에 한 번 말해 두어야 나중의 읽기가 소리 난다.
  try {
    const synth = window.speechSynthesis
    if (!synth || !window.SpeechSynthesisUtterance) return
    const u = new SpeechSynthesisUtterance(' ')
    u.volume = 0
    synth.speak(u)
  } catch { /* 읽기 미지원 → 화면 글로 안내 */ }
}

export function CallProvider({ children }: { children: ReactNode }) {
  const { settings } = useSettings()
  const residentId = settings.residentId

  const [phase, setPhaseState] = useState<Phase>('idle')
  const [callId, setCallId] = useState<number | null>(null)
  const [result, setResult] = useState<TurnResult | null>(null)
  const [voice, setVoice] = useState<Voice>('idle')
  const [heard, setHeard] = useState<Heard>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [micProblem, setMicProblemState] = useState<MicProblem>(null)
  const [sttHint, setSttHint] = useState('')
  const [ttsNotice, setTtsNotice] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const [textOpen, setTextOpenState] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [ringError, setRingError] = useState<string | null>(null)
  const [homeVersion, setHomeVersion] = useState(0)
  const [kick, setKick] = useState(0)

  const phaseRef = useRef<Phase>('idle')
  const callIdRef = useRef<number | null>(null)
  const resultRef = useRef<TurnResult | null>(null)
  const settingsRef = useRef(settings)
  settingsRef.current = settings
  const micProblemRef = useRef<MicProblem>(null)
  const textOpenRef = useRef(false)
  const holdRef = useRef(false)
  const busyRef = useRef(false)
  const pendingRef = useRef<TurnRequest | null>(null)
  const turnSeq = useRef(0)
  const listenWindow = useRef(false)
  const interimRef = useRef('')
  const silenceTimer = useRef<number | null>(null)
  const skipRef = useRef(false)
  const resumingRef = useRef(false)
  const inputRef = useRef<SpeechInput | null>(null)
  const outputRef = useRef<SpeechOutput | null>(null)

  const setPhase = useCallback((p: Phase) => { phaseRef.current = p; setPhaseState(p) }, [])
  const setMicProblem = useCallback((p: MicProblem) => { micProblemRef.current = p; setMicProblemState(p) }, [])
  const setTextOpen = useCallback((open: boolean) => { textOpenRef.current = open; setTextOpenState(open) }, [])

  const clearSilence = useCallback(() => {
    if (silenceTimer.current !== null) { clearTimeout(silenceTimer.current); silenceTimer.current = null }
  }, [])

  // 늦게 만들어 순환 참조를 피한다: submit ↔ 음성 콜백
  const submitRef = useRef<(text: string, source: TurnSource) => void>(() => {})
  const startListeningRef = useRef<() => void>(() => {})

  const armSilence = useCallback(() => {
    clearSilence()
    silenceTimer.current = window.setTimeout(() => {
      silenceTimer.current = null
      if (!listenWindow.current) return
      listenWindow.current = false
      inputRef.current?.stop()
      const said = interimRef.current.trim()
      // 말하다 끊긴 문장이 있으면 그것을, 아무 말도 없으면 '조용함'을 보낸다.
      submitRef.current(said, said ? 'stt' : 'silence')
    }, SILENCE_MS)
  }, [clearSilence])

  const onSttState = useCallback((s: SttState) => {
    if (s.listening === true) setVoice(s.sttStatus === 'listening' ? 'listening' : 'starting')
    else if (s.listening === false) setVoice((v) => (v === 'listening' || v === 'starting' ? 'idle' : v))
    if (s.interimTranscript) {
      interimRef.current = s.interimTranscript
      setHeard({ text: s.interimTranscript, kind: 'interim' })
      if (listenWindow.current) armSilence()
    }
    const code = s.sttErrorCode
    if (!code) { if (s.sttError === '') setSttHint(''); return }
    if (MIC_UNAVAILABLE.has(code)) {
      listenWindow.current = false
      clearSilence()
      setMicProblem({ message: s.sttError ?? '', code })
    } else if (code === 'no-speech' && listenWindow.current) {
      // 브라우저가 몇 초 만에 듣기를 끝내도, 10초가 될 때까지는 조용히 다시 듣는다.
      window.setTimeout(() => {
        if (listenWindow.current && phaseRef.current === 'talk' && !inputRef.current?.active) {
          if (!inputRef.current?.start()) { listenWindow.current = false; clearSilence() }
        }
      }, 200)
    } else if (code !== 'no-speech') {
      listenWindow.current = false
      clearSilence()
      setSttHint(s.sttError ?? '')
    }
  }, [armSilence, clearSilence, setMicProblem])

  const onFinal = useCallback((text: string) => {
    listenWindow.current = false
    clearSilence()
    setHeard({ text, kind: 'stt' })
    submitRef.current(text, 'stt')
  }, [clearSilence])

  useEffect(() => {
    const input = new SpeechInput({
      host: window as unknown as RecognitionHost,
      canStart: () => phaseRef.current === 'talk' && !outputRef.current?.speaking,
      onState: onSttState,
      onFinal,
    })
    const output = new SpeechOutput({
      host: window as unknown as SynthesisHost,
      beforeSpeak: () => { listenWindow.current = false; clearSilence(); input.stop() },
      onState: (s) => { if (s.speaking) setVoice('speaking'); else setVoice((v) => (v === 'speaking' ? 'idle' : v)) },
      onNotice: setTtsNotice,
      enabled: () => true,
      rate: () => settingsRef.current.rate,
    })
    inputRef.current = input
    outputRef.current = output
    return () => { input.dispose(); output.dispose(); clearSilence() }
  }, [onSttState, onFinal, clearSilence])

  const startListening = useCallback(() => {
    const input = inputRef.current
    if (!input || phaseRef.current !== 'talk' || micProblemRef.current || busyRef.current || textOpenRef.current || holdRef.current) return
    if (outputRef.current?.speaking) return
    setSttHint('')
    interimRef.current = ''
    setHeard(null)
    listenWindow.current = true
    if (input.start()) armSilence()
    else listenWindow.current = false
  }, [armSilence])
  startListeningRef.current = startListening

  const present = useCallback((r: TurnResult) => {
    resultRef.current = r
    setResult(r)
    setSelected(null)
    setError(null)
    const key = `${callIdRef.current}:${++turnSeq.current}`
    const output = outputRef.current
    if (!output) return
    output.speak(r.ai_text, key).then((proceed) => {
      const skipped = skipRef.current
      skipRef.current = false
      if (!proceed || phaseRef.current !== 'talk' || resultRef.current !== r) return
      if (r.finished) { setPhase('done'); return }
      if (settingsRef.current.autoListen || skipped) startListeningRef.current()
      else setVoice('idle')
    })
  }, [setPhase])

  const endLocally = useCallback((message: string | null) => {
    listenWindow.current = false
    clearSilence()
    inputRef.current?.stop()
    outputRef.current?.stop(false)
    busyRef.current = false
    pendingRef.current = null
    callIdRef.current = null
    resultRef.current = null
    setCallId(null)
    setResult(null)
    setHeard(null)
    setSelected(null)
    setError(null)
    setTextOpen(false)
    setVoice('idle')
    setNotice(message)
    setPhase('idle')
    setHomeVersion((v) => v + 1)
  }, [clearSilence, setPhase, setTextOpen])

  const send = useCallback((req: TurnRequest) => {
    const id = callIdRef.current
    if (id === null) return
    busyRef.current = true
    pendingRef.current = req
    setError(null)
    setVoice('sending')
    api.turn(id, req).then((r) => {
      if (callIdRef.current !== id) return
      busyRef.current = false
      pendingRef.current = null
      if (req.source === 'text') { setDraft(''); setTextOpen(false) }
      present(r)
    }).catch((e: unknown) => {
      if (callIdRef.current !== id) return
      busyRef.current = false
      if (e instanceof ApiError && (e.status === 404 || e.status === 409)) { endLocally(e.message || '이 전화는 이미 끝났어요.'); return }
      setError(friendly(e))
      setVoice('idle')
    })
  }, [present, endLocally, setTextOpen])

  const submit = useCallback((text: string, source: TurnSource) => {
    if (callIdRef.current === null || busyRef.current || phaseRef.current !== 'talk') return
    listenWindow.current = false
    clearSilence()
    inputRef.current?.stop()
    outputRef.current?.stop(false)
    const pending = pendingRef.current
    // 실패했던 답을 그대로 다시 보내면 같은 client_turn_id를 써서 서버가 두 번 저장하지 않게 한다.
    if (pending && pending.text === text && pending.source === source) send(pending)
    else send({ text, source, client_turn_id: newTurnId() })
  }, [clearSilence, send])
  submitRef.current = submit

  const beginTalk = useCallback((id: number, r: TurnResult) => {
    callIdRef.current = id
    setCallId(id)
    setNotice(null)
    setRingError(null)
    setHeard(null)
    setDraft('')
    setTtsNotice('')
    setSttHint('')
    const host = window as unknown as RecognitionHost
    if (!host.SpeechRecognition && !host.webkitSpeechRecognition) setMicProblem({ message: '이 브라우저는 음성 인식을 지원하지 않아요.', code: 'unsupported' })
    else if (window.isSecureContext === false) setMicProblem({ message: '마이크는 HTTPS 주소나 localhost에서만 쓸 수 있어요.', code: 'insecure' })
    else setMicProblem(null)
    setPhase('talk')
    present(r)
  }, [present, setMicProblem, setPhase])

  const resume = useCallback((id: number) => {
    if (resumingRef.current) return
    resumingRef.current = true
    api.call(id).then((c) => {
      if (c.status !== 'in_progress' || phaseRef.current === 'talk') return
      const q = c.question
      beginTalk(id, {
        ai_text: q ? `이어서 여쭐게요. ${q}` : '', empathy: null, question: q, topic: null, options: [],
        step: c.step ?? { index: 1, total: 5 }, action: 'next', safety: false, finished: false, llm_used: false,
      })
    }).catch(() => { /* 다음 확인 때 다시 시도 */ }).finally(() => { resumingRef.current = false })
  }, [beginTalk])

  // ── 벨 확인: 화면이 보이고, 통화 중이 아닐 때만 2초마다 ──
  useEffect(() => {
    if (residentId === null || (phase !== 'idle' && phase !== 'ringing')) return
    let stopped = false, inFlight = false
    const handle = (inc: Incoming) => {
      const p = phaseRef.current
      if (p === 'idle') {
        if (inc.ringing) {
          callIdRef.current = inc.ringing.call_id
          setCallId(inc.ringing.call_id)
          setNotice(null)
          setRingError(null)
          setPhase('ringing')
        } else if (inc.active) resume(inc.active.call_id)
      } else if (p === 'ringing') {
        if (inc.ringing?.call_id === callIdRef.current) return
        if (inc.active && inc.active.call_id === callIdRef.current) { setPhase('idle'); resume(inc.active.call_id); return }
        callIdRef.current = null
        setCallId(null)
        setNotice(MISSED_NOTICE)
        setPhase('idle')
        setHomeVersion((v) => v + 1)
      }
    }
    const tick = () => {
      if (stopped || inFlight || document.visibilityState !== 'visible') return
      inFlight = true
      api.incoming(residentId).then((inc) => { if (!stopped) handle(inc) }).catch(() => {}).finally(() => { inFlight = false })
    }
    tick()
    const timer = window.setInterval(tick, POLL_MS)
    const onVisible = () => { if (document.visibilityState === 'visible') tick() }
    document.addEventListener('visibilitychange', onVisible)
    return () => { stopped = true; clearInterval(timer); document.removeEventListener('visibilitychange', onVisible) }
  }, [residentId, phase, kick, resume, setPhase])

  const ringMe = useCallback(async () => {
    if (residentId === null) return
    try {
      await api.ringMe(residentId)
    } catch (e) {
      if (!(e instanceof ApiError && e.status === 409)) throw e
    }
    setKick((k) => k + 1)
  }, [residentId])

  const answer = useCallback(() => {
    const id = callIdRef.current
    if (id === null || phaseRef.current !== 'ringing') return
    unlockSpeech()
    setRingError(null)
    setPhase('answering')
    api.answer(id).then((r) => beginTalk(id, r)).catch((e: unknown) => {
      if (e instanceof ApiError && (e.status === 404 || e.status === 409)) { endLocally(MISSED_NOTICE); return }
      setRingError(friendly(e))
      setPhase('ringing')
    })
  }, [beginTalk, endLocally, setPhase])

  const decline = useCallback(() => {
    const id = callIdRef.current
    if (id === null) return
    api.decline(id).catch(() => { /* 서버가 30초 뒤 미응답으로 닫는다 */ })
    endLocally(null)
  }, [endLocally])

  const choose = useCallback((option: string) => {
    if (busyRef.current) return
    setSelected(option)
    setHeard({ text: option, kind: 'option' })
    submit(option, 'option')
  }, [submit])

  const sendText = useCallback(() => {
    const text = draft.trim()
    if (!text || busyRef.current) return
    setHeard({ text, kind: 'text' })
    submit(text, 'text')
  }, [draft, submit])

  const toggleMic = useCallback(() => {
    if (voice === 'speaking') { skipRef.current = true; outputRef.current?.stop(true); return }
    if (voice === 'listening' || voice === 'starting') {
      listenWindow.current = false
      clearSilence()
      inputRef.current?.stop({ manual: true })
      return
    }
    if (voice === 'idle') startListening()
  }, [voice, clearSilence, startListening])

  const retryMic = useCallback(() => {
    setMicProblem(null)
    startListening()
  }, [setMicProblem, startListening])

  const retry = useCallback(() => {
    if (pendingRef.current && !busyRef.current) send(pendingRef.current)
  }, [send])

  const stopMicForHold = useCallback(() => {
    listenWindow.current = false
    clearSilence()
    inputRef.current?.stop({ manual: true })
  }, [clearSilence])

  const openText = useCallback((open: boolean) => {
    if (open) stopMicForHold()
    setTextOpen(open)
    if (!open && settingsRef.current.autoListen) startListening()
  }, [stopMicForHold, setTextOpen, startListening])

  /** 끊기 확인 창이 떠 있는 동안에는 마이크를 쉬게 한다(조용함이 대신 보내지지 않도록). */
  const hold = useCallback((on: boolean) => {
    holdRef.current = on
    if (on) stopMicForHold()
    else if (settingsRef.current.autoListen) startListening()
  }, [stopMicForHold, startListening])

  const hangup = useCallback(async () => {
    const id = callIdRef.current
    if (id === null) return
    listenWindow.current = false
    clearSilence()
    inputRef.current?.stop()
    outputRef.current?.stop(false)
    try {
      await api.hangup(id)
    } catch (e) {
      if (!(e instanceof ApiError && (e.status === 404 || e.status === 409))) throw new Error(friendly(e))
    }
    holdRef.current = false
    endLocally(ENDED_NOTICE)
  }, [clearSilence, endLocally])

  const finish = useCallback(() => endLocally(null), [endLocally])
  const dismissNotice = useCallback(() => setNotice(null), [])

  const value = useMemo<CallCtx>(() => ({
    phase, callId, result, voice, heard, selected, micProblem, sttHint, ttsNotice, error, draft, textOpen, notice, ringError, homeVersion,
    setDraft, setTextOpen: openText, ringMe, answer, decline, choose, sendText, toggleMic, retryMic, retry, hold, hangup, finish, dismissNotice,
  }), [phase, callId, result, voice, heard, selected, micProblem, sttHint, ttsNotice, error, draft, textOpen, notice, ringError, homeVersion,
    openText, ringMe, answer, decline, choose, sendText, toggleMic, retryMic, retry, hold, hangup, finish, dismissNotice])

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export function useCall(): CallCtx {
  const ctx = useContext(Ctx)
  if (!ctx) throw new Error('CallProvider missing')
  return ctx
}
