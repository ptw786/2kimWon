// 음성 출력(TTS). ansimon-fullstack/frontend/src/speech/synthesis.js를 TypeScript로 옮겼다.
// 바뀐 점: 말하는 속도를 설정에서 받는다(rate, 기본 0.86).

export type TtsState = { speaking: boolean; speakingText: string }

export interface UtteranceLike {
  text?: string
  lang: string
  rate: number
  voice?: unknown
  onend: (() => void) | null
  onerror: (() => void) | null
}

export type SynthesisHost = {
  speechSynthesis?: {
    getVoices?: () => { lang: string }[]
    speak: (utterance: UtteranceLike) => void
    cancel: () => void
  } | null
  SpeechSynthesisUtterance?: new (text: string) => UtteranceLike
  setTimeout: (fn: () => void, ms: number) => number
  clearTimeout: (id: number | null | undefined) => void
}

type Task = {
  key: string
  promise: Promise<boolean>
  timer: number | null
  utterance: UtteranceLike | null
  settle: (proceed: boolean) => void
}

type OutputOptions = {
  host: SynthesisHost
  beforeSpeak: () => void
  onState: (state: TtsState) => void
  onNotice: (notice: string) => void
  enabled: () => boolean
  rate?: () => number
}

export const DEFAULT_RATE = 0.86

/** Event-driven output with one utterance and stable per-dialogue-stage keys. */
export class SpeechOutput {
  host: SynthesisHost
  beforeSpeak: () => void
  onState: (state: TtsState) => void
  onNotice: (notice: string) => void
  enabled: () => boolean
  rate: () => number
  task: Task | null = null
  completed = new Set<string>()
  disposed = false

  constructor({ host, beforeSpeak, onState, onNotice, enabled, rate = () => DEFAULT_RATE }: OutputOptions) {
    this.host = host
    this.beforeSpeak = beforeSpeak
    this.onState = onState
    this.onNotice = onNotice
    this.enabled = enabled
    this.rate = rate
  }

  get speaking(): boolean {
    return this.task !== null
  }

  /** 끝까지 읽으면 true, 중간에 멈추면(stop(false)) false로 끝난다. */
  speak(text: string, key: string = text): Promise<boolean> {
    if (this.disposed) return Promise.resolve(false)
    if (!text || !this.enabled()) return Promise.resolve(true)
    if (this.task?.key === key) return this.task.promise
    if (this.completed.has(key)) return Promise.resolve(true)
    this.stop(false)
    this.beforeSpeak() // Always close STT, even if a caller forgot to do so.
    const synthesis = this.host.speechSynthesis, Utterance = this.host.SpeechSynthesisUtterance
    if (!synthesis || !Utterance) {
      this.completed.add(key)
      this.onNotice('이 폰은 소리로 읽어 주기를 지원하지 않아 화면의 글로 안내해요.')
      return Promise.resolve(true)
    }
    let resolve!: (value: boolean) => void
    const promise = new Promise<boolean>((done) => { resolve = done })
    const task: Task = { key, promise, timer: null, utterance: null, settle: () => {} }
    this.task = task
    const settle = (proceed: boolean) => {
      if (this.task !== task) return
      this.host.clearTimeout(task.timer)
      if (task.utterance) { task.utterance.onend = null; task.utterance.onerror = null }
      this.task = null
      if (proceed) this.completed.add(key)
      if (!this.disposed) this.onState({ speaking: false, speakingText: '' })
      resolve(proceed)
    }
    task.settle = settle
    try {
      const speech = new Utterance(text); task.utterance = speech
      speech.lang = 'ko-KR'; speech.rate = this.rate()
      const voice = synthesis.getVoices?.().find((v) => /^ko(?:-|$)/i.test(v.lang))
      if (voice) speech.voice = voice
      speech.onend = () => settle(true)
      speech.onerror = () => { if (this.task === task) { this.onNotice('소리를 내지 못해 화면의 글로 안내해요.'); settle(true) } }
      task.timer = this.host.setTimeout(() => {
        if (this.task !== task) return
        this.onNotice('소리가 늦어져 화면의 글로 안내해요.')
        settle(true); synthesis.cancel()
      }, Math.min(60000, Math.max(8000, text.length * 450)))
      this.onState({ speaking: true, speakingText: text })
      synthesis.speak(speech)
    } catch {
      this.onNotice('소리를 내지 못해 화면의 글로 안내해요.')
      settle(true)
      try { synthesis.cancel() } catch { /* ignore */ }
    }
    return promise
  }
  stop(continueSequence = false): void {
    this.task?.settle(continueSequence)
    try { this.host.speechSynthesis?.cancel() } catch { /* ignore */ }
  }
  dispose(): void {
    this.disposed = true
    this.stop(false)
    this.completed.clear()
  }
}
