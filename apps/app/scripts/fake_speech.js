// Playwright 초기화 스크립트: 브라우저의 읽기(TTS)·듣기(STT)를 가짜로 바꾼다.
// window.__say: 듣기를 시작할 때마다 하나씩 꺼내 쓰는 대본.
//   '문장'           → 0.4초 뒤 최종 인식 결과
//   'INTERIM:문장'   → 중간 결과만 보내고 계속 듣는 중
//   'SILENT'         → 크롬처럼 4초 뒤 no-speech 오류
//   (비어 있음/HOLD) → 아무 일도 없이 계속 듣는 중
(() => {
  const log = (window.__speechLog = [])
  window.__say = []
  window.__ttsMs = 300
  const now = () => Math.round(performance.now())
  class FakeUtterance {
    constructor(text) { this.text = text; this.lang = ''; this.rate = 1; this.volume = 1; this.onend = null; this.onerror = null }
  }
  const synth = {
    getVoices: () => [{ lang: 'ko-KR', name: 'fake-ko' }],
    speak(u) {
      if (!u.text || !u.text.trim()) return // 잠금 해제용 빈 문장
      log.push({ t: now(), ev: 'tts-start', text: u.text, rate: u.rate })
      u.__timer = setTimeout(() => { log.push({ t: now(), ev: 'tts-end', text: u.text }); u.onend && u.onend() }, window.__ttsMs)
      synth.__last = u
    },
    cancel() { if (synth.__last) { clearTimeout(synth.__last.__timer); synth.__last = null } },
  }
  Object.defineProperty(window, 'speechSynthesis', { value: synth, configurable: true })
  window.SpeechSynthesisUtterance = FakeUtterance
  const result = (text, isFinal) => ({ resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal })] })
  class FakeRecognition {
    constructor() { this.onstart = this.onresult = this.onerror = this.onend = this.onnomatch = null; this.dead = false }
    start() {
      window.__rec = this
      log.push({ t: now(), ev: 'stt-start' })
      setTimeout(() => !this.dead && this.onstart && this.onstart(), 50)
      const line = window.__say.shift()
      if (!line || line === 'HOLD') return
      if (line === 'SILENT') { setTimeout(() => !this.dead && this.onerror && this.onerror({ error: 'no-speech' }), 4000); return }
      if (line.startsWith('INTERIM:')) { setTimeout(() => !this.dead && this.onresult && this.onresult(result(line.slice(8), false)), 300); return }
      setTimeout(() => !this.dead && this.onresult && this.onresult(result(line.slice(0, 4), false)), 150)
      setTimeout(() => { if (!this.dead && this.onresult) { log.push({ t: now(), ev: 'stt-final', text: line }); this.onresult(result(line, true)) } }, 400)
    }
    abort() { if (!this.dead) log.push({ t: now(), ev: 'stt-stop' }); this.dead = true }
    stop() { this.abort() }
  }
  if (!window.__noMic) window.SpeechRecognition = FakeRecognition
})()
