// 음성 인식(STT) 한 세션을 책임진다. ansimon-fullstack/frontend/src/speech/recognition.js를 TypeScript로 옮겼다.
// 동작은 그대로 두고, 화면이 오류 종류를 구분할 수 있게 sttErrorCode만 더했다.

export type SttStatus = 'idle' | 'starting' | 'listening'

export type SttState = {
  sttStatus?: SttStatus
  listening?: boolean
  interimTranscript?: string
  lastTranscript?: string
  sttError?: string
  sttErrorCode?: string
  sttNotice?: string
}

type RecognitionResult = ArrayLike<{ transcript: string }> & { isFinal?: boolean }
export type RecognitionEvent = { resultIndex?: number; results: ArrayLike<RecognitionResult> }

export interface RecognitionLike {
  lang: string
  continuous: boolean
  interimResults: boolean
  maxAlternatives: number
  onstart: (() => void) | null
  onresult: ((event: RecognitionEvent) => void) | null
  onerror: ((event: { error: string }) => void) | null
  onend: (() => void) | null
  onnomatch: (() => void) | null
  start(): void
  abort(): void
}

export type RecognitionHost = {
  SpeechRecognition?: new () => RecognitionLike
  webkitSpeechRecognition?: new () => RecognitionLike
  isSecureContext?: boolean
  setTimeout: (fn: () => void, ms: number) => number
  clearTimeout: (id: number | null | undefined) => void
}

const TAIL = '버튼이나 글자로 답해 주세요.'
const ERRORS: Record<string, string> = {
  'not-allowed': `마이크 권한이 거부되어 있어요. ${TAIL}`,
  'service-not-allowed': `이 폰에서는 음성 인식을 쓸 수 없어요. ${TAIL}`,
  'audio-capture': `마이크를 찾지 못했어요. ${TAIL}`,
  'no-speech': `말씀을 듣지 못했어요. 다시 말씀하시거나 ${TAIL}`,
  network: `음성 인식에 연결하지 못했어요. ${TAIL}`,
  aborted: `듣기가 멈췄어요. 다시 누르시거나 ${TAIL}`,
  'language-not-supported': `이 폰에서는 한국어 음성 인식을 쓸 수 없어요. ${TAIL}`,
  unsupported: `이 브라우저는 음성 인식을 지원하지 않아요. ${TAIL}`,
  insecure: `마이크는 HTTPS 주소나 localhost에서만 쓸 수 있어요. ${TAIL}`,
}
export const recognitionMessage = (code: string): string =>
  ERRORS[code] || `음성 인식에 실패했어요. 다시 누르시거나 ${TAIL}`

/** 다시 눌러도 소용없는 오류: 이때는 마이크 대신 버튼·글자로만 답한다. */
export const MIC_UNAVAILABLE = new Set(['unsupported', 'insecure', 'not-allowed', 'service-not-allowed', 'audio-capture', 'language-not-supported'])

type Session = { rec: RecognitionLike; timer: number | null }

type InputOptions = {
  host: RecognitionHost
  canStart: () => boolean
  onState: (state: SttState) => void
  onFinal: (text: string) => void
  timeout?: number
}

/** Owns exactly one recognition session, including the time before onstart. */
export class SpeechInput {
  host: RecognitionHost
  canStart: () => boolean
  onState: (state: SttState) => void
  onFinal: (text: string) => void
  timeout: number
  session: Session | null = null
  disposed = false

  constructor({ host, canStart, onState, onFinal, timeout = 30000 }: InputOptions) {
    this.host = host
    this.canStart = canStart
    this.onState = onState
    this.onFinal = onFinal
    this.timeout = timeout
  }

  get supported(): boolean {
    return Boolean(this.host.SpeechRecognition || this.host.webkitSpeechRecognition)
  }
  get active(): boolean {
    return this.session !== null
  }
  emit(state: SttState): void {
    if (!this.disposed) this.onState(state)
  }
  close(session: Session): void {
    if (this.session !== session) return
    this.session = null
    this.host.clearTimeout(session.timer)
    const rec = session.rec
    rec.onstart = null; rec.onresult = null; rec.onerror = null; rec.onend = null; rec.onnomatch = null
    try { rec.abort() } catch { /* already closed */ }
  }
  fail(session: Session, code: string): void {
    if (this.session !== session || this.disposed) return
    this.close(session)
    this.emit({ sttStatus: 'idle', listening: false, interimTranscript: '', sttError: recognitionMessage(code), sttErrorCode: code, sttNotice: '' })
  }
  start(): boolean {
    if (this.disposed || this.active || !this.canStart()) return false
    const Recognition = this.host.SpeechRecognition || this.host.webkitSpeechRecognition
    if (!Recognition) {
      this.emit({ sttError: recognitionMessage('unsupported'), sttErrorCode: 'unsupported', sttNotice: '', sttStatus: 'idle', listening: false })
      return false
    }
    if (this.host.isSecureContext === false) {
      this.emit({ sttError: recognitionMessage('insecure'), sttErrorCode: 'insecure', sttNotice: '', sttStatus: 'idle', listening: false })
      return false
    }
    let session: Session | undefined
    try {
      const rec = new Recognition()
      const current: Session = { rec, timer: null }
      session = current
      this.session = current
      rec.lang = 'ko-KR'; rec.continuous = false; rec.interimResults = true; rec.maxAlternatives = 1
      const live = () => !this.disposed && this.session === current
      // Lock synchronously: a second click before onstart cannot open another mic.
      this.emit({ sttStatus: 'starting', listening: true, interimTranscript: '', lastTranscript: '', sttError: '', sttErrorCode: '', sttNotice: '마이크를 켜고 있어요.' })
      rec.onstart = () => { if (live()) this.emit({ sttStatus: 'listening', listening: true, sttNotice: '듣고 있어요. 말씀해 주세요.' }) }
      rec.onresult = (event) => {
        if (!live()) return
        const final: string[] = [], interim: string[] = []
        for (let i = event.resultIndex || 0; i < event.results.length; i++) {
          const result = event.results[i], text = result?.[0]?.transcript || ''
          if (result.isFinal === true) final.push(text)
          else interim.push(text)
        }
        if (final.join(' ').trim()) {
          const text = final.join(' ').trim()
          this.close(current) // Detach and abort before any TTS/API processing.
          this.emit({ sttStatus: 'idle', listening: false, interimTranscript: '', lastTranscript: text, sttError: '', sttErrorCode: '', sttNotice: '말씀을 들었어요.' })
          this.onFinal(text)
        } else if (interim.join(' ').trim()) this.emit({ interimTranscript: interim.join(' ').trim() })
      }
      rec.onerror = (event) => this.fail(current, event.error)
      rec.onnomatch = () => this.fail(current, 'no-speech')
      rec.onend = () => { if (live()) this.fail(current, 'no-speech') }
      current.timer = this.host.setTimeout(() => this.fail(current, 'no-speech'), this.timeout)
      rec.start()
      return true
    } catch (error) {
      if (session) this.close(session)
      const name = (error as { name?: string } | null)?.name ?? ''
      const code = ['NotAllowedError', 'SecurityError'].includes(name) ? 'not-allowed' : 'start-failed'
      this.emit({ sttStatus: 'idle', listening: false, interimTranscript: '', sttError: recognitionMessage(code), sttErrorCode: code, sttNotice: '' })
      return false
    }
  }
  stop({ manual = false }: { manual?: boolean } = {}): void {
    const session = this.session
    if (!session) return
    this.close(session)
    this.emit({
      sttStatus: 'idle', listening: false, interimTranscript: '',
      sttNotice: manual ? '듣기를 멈췄어요. 버튼이나 글자로 답할 수 있어요.' : '',
      ...(manual ? { sttError: '', sttErrorCode: '' } : {}),
    })
  }
  dispose(): void {
    this.disposed = true
    if (this.session) this.close(this.session)
  }
}
