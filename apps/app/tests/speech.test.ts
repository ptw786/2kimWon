// ansimon-fullstack/frontend/tests/speech.test.js를 옮겨 왔다. 문구는 해요체·'글자로'로 바뀌었고,
// 오류 종류(sttErrorCode)와 말하는 속도(rate) 확인을 더했다. 실행: npm test (vitest)
import { test } from 'vitest'
import assert from 'node:assert/strict'
import { SpeechInput, recognitionMessage, MIC_UNAVAILABLE, type RecognitionHost, type SttState } from '../src/features/call/speech/recognition.ts'
import { SpeechOutput, type SynthesisHost, type TtsState } from '../src/features/call/speech/synthesis.ts'

type FakeRec = {
  aborts: number; starts: number; lang?: string; interimResults?: boolean; continuous?: boolean
  onstart: (() => void) | null; onresult: ((e: unknown) => void) | null; onerror: ((e: { error: string }) => void) | null
  onend: (() => void) | null; onnomatch: (() => void) | null
}

function inputFixture({ webkit = false, supported = true, canStart = () => true, throwStart = false } = {}) {
  const instances: FakeRec[] = [], states: SttState[] = [], answers: string[] = [], timers = new Map<number, () => void>()
  let serial = 0
  class Recognition {
    aborts = 0; starts = 0
    onstart = null; onresult = null; onerror = null; onend = null; onnomatch = null
    constructor() { instances.push(this as unknown as FakeRec) }
    start() { this.starts++; if (throwStart) throw Object.assign(new Error('denied'), { name: 'NotAllowedError' }) }
    abort() { this.aborts++ }
  }
  const host: Record<string, unknown> = {
    isSecureContext: true,
    setTimeout: (fn: () => void) => { timers.set(++serial, fn); return serial },
    clearTimeout: (id: number) => timers.delete(id),
  }
  if (supported) host[webkit ? 'webkitSpeechRecognition' : 'SpeechRecognition'] = Recognition
  const input = new SpeechInput({ host: host as unknown as RecognitionHost, canStart, onState: (s) => states.push(s), onFinal: (t) => answers.push(t) })
  return { input, host, instances, states, answers, timers }
}
function emit(rec: FakeRec, text: string, final = true) {
  rec.onresult?.({ resultIndex: 0, results: [Object.assign([{ transcript: text }], { isFinal: final })] })
}

test('Korean options and synchronous duplicate-start lock cover the pre-onstart window', () => {
  const { input, instances, states } = inputFixture()
  assert.equal(input.start(), true); assert.equal(input.start(), false)
  assert.equal(instances.length, 1); assert.equal(instances[0].starts, 1)
  assert.equal(instances[0].lang, 'ko-KR'); assert.equal(instances[0].interimResults, true)
  assert.equal(instances[0].continuous, false); assert.equal(states[0].sttStatus, 'starting')
  instances[0].onstart!(); assert.equal(states.at(-1)!.sttStatus, 'listening')
})
test('interim text is shown; final is delivered once and late callbacks cannot resubmit', () => {
  const { input, instances, states, answers, timers } = inputFixture(); input.start()
  const rec = instances[0], late = rec.onresult!
  emit(rec, '안 아', false); assert.equal(answers.length, 0); assert.equal(states.at(-1)!.interimTranscript, '안 아')
  emit(rec, '안 아파', true); assert.deepEqual(answers, ['안 아파']); assert.equal(input.active, false)
  late({ results: [Object.assign([{ transcript: '가짜 늦은 답변' }], { isFinal: true })] })
  assert.equal(answers.length, 1); assert.equal(rec.aborts, 1); assert.equal(timers.size, 0)
})
test('manual stop discards post-stop final results and permits a fresh session', () => {
  const { input, instances, answers, states } = inputFixture(); input.start()
  const late = instances[0].onresult!; input.stop({ manual: true })
  late({ results: [Object.assign([{ transcript: '안 아파' }], { isFinal: true })] })
  assert.equal(answers.length, 0); assert.equal(states.at(-1)!.listening, false)
  assert.match(states.at(-1)!.sttNotice!, /멈췄/); assert.equal(input.start(), true)
  assert.equal(instances.length, 2)
})
for (const code of ['not-allowed', 'service-not-allowed', 'audio-capture', 'no-speech', 'network', 'aborted', 'language-not-supported', 'other']) {
  test(`recognition error ${code} releases the mic and provides a button/text fallback`, () => {
    const { input, instances, states } = inputFixture(); input.start(); instances[0].onerror!({ error: code })
    assert.equal(input.active, false); assert.equal(instances[0].aborts, 1)
    assert.equal(states.at(-1)!.sttError, recognitionMessage(code)); assert.match(states.at(-1)!.sttError!, /글자로/)
    assert.equal(states.at(-1)!.sttErrorCode, code)
    assert.equal(input.start(), true)
  })
}
test('webkitSpeechRecognition fallback works', () => { const f = inputFixture({ webkit: true }); assert.equal(f.input.start(), true); assert.equal(f.instances[0].lang, 'ko-KR') })
test('unsupported API leaves text input available with an actionable message', () => {
  const f = inputFixture({ supported: false }); assert.equal(f.input.start(), false)
  assert.match(f.states.at(-1)!.sttError!, /지원하지 않아요/); assert.equal(f.states.at(-1)!.sttErrorCode, 'unsupported')
  assert.ok(MIC_UNAVAILABLE.has('unsupported')); assert.equal(f.instances.length, 0)
})
test('insecure context does not start a microphone', () => {
  const f = inputFixture(); (f.host as { isSecureContext: boolean }).isSecureContext = false
  assert.equal(f.input.start(), false); assert.match(f.states.at(-1)!.sttError!, /HTTPS/); assert.equal(f.states.at(-1)!.sttErrorCode, 'insecure'); assert.equal(f.instances.length, 0)
})
test('synchronous permission failure cleans up and names the denied permission', () => {
  const f = inputFixture({ throwStart: true }); assert.equal(f.input.start(), false); assert.equal(f.input.active, false)
  assert.match(f.states.at(-1)!.sttError!, /권한이 거부/); assert.equal(f.timers.size, 0)
})
test('no-result end and recognition deadline do not leave listening active', () => {
  const f = inputFixture(); f.input.start(); f.instances[0].onend!(); assert.equal(f.input.active, false)
  f.input.start(); [...f.timers.values()][0](); assert.equal(f.input.active, false); assert.match(f.states.at(-1)!.sttError!, /듣지 못했/)
})
test('call/TTS guards prevent recognition from starting', () => { const f = inputFixture({ canStart: () => false }); assert.equal(f.input.start(), false); assert.equal(f.instances.length, 0) })
test('dispose removes callbacks and prevents later state writes', () => {
  const f = inputFixture(); f.input.start(); const late = f.instances[0].onerror!; f.input.dispose(); const count = f.states.length
  late({ error: 'network' }); assert.equal(f.states.length, count); assert.equal(f.instances[0].onresult, null); assert.equal(f.input.start(), false)
})

type FakeUtt = { text: string; lang: string; rate: number; voice?: unknown; onend: (() => void) | null; onerror: (() => void) | null }
function outputFixture(rate?: () => number) {
  const states: TtsState[] = [], notices: string[] = [], spoken: FakeUtt[] = [], timers = new Map<number, () => void>()
  let serial = 0, cancelled = 0, stoppedMic = 0, enabled = true
  const ko = { lang: 'ko-KR', name: 'Korean' }
  const host: Record<string, unknown> = {
    setTimeout: (fn: () => void) => { timers.set(++serial, fn); return serial },
    clearTimeout: (id: number) => timers.delete(id),
    SpeechSynthesisUtterance: class { text: string; constructor(text: string) { this.text = text } },
    speechSynthesis: { getVoices: () => [{ lang: 'en-US' }, ko], speak: (s: FakeUtt) => spoken.push(s), cancel: () => cancelled++ },
  }
  const output = new SpeechOutput({
    host: host as unknown as SynthesisHost, beforeSpeak: () => stoppedMic++, onState: (s) => states.push(s),
    onNotice: (n) => notices.push(n), enabled: () => enabled, ...(rate ? { rate } : {}),
  })
  return { output, host, states, notices, spoken, timers, ko, get cancelled() { return cancelled }, get stoppedMic() { return stoppedMic }, mute: () => { enabled = false } }
}
test('TTS stops recognition first, selects Korean, uses the default slow rate and settles only after end', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0')
  assert.equal(f.stoppedMic, 1); assert.equal(f.spoken[0].lang, 'ko-KR'); assert.equal(f.spoken[0].voice, f.ko)
  assert.equal(f.spoken[0].rate, 0.86); assert.equal(f.output.speaking, true)
  assert.equal(f.states.at(-1)!.speaking, true); f.spoken[0].onend!(); assert.equal(await promise, true)
  assert.equal(f.states.at(-1)!.speaking, false); assert.equal(f.timers.size, 0); assert.equal(f.output.speaking, false)
})
test('speaking rate follows the setting at the moment of speaking', () => {
  let rate = 1
  const f = outputFixture(() => rate); f.output.speak('하나', 'a'); assert.equal(f.spoken[0].rate, 1)
  rate = 0.86; f.output.speak('둘', 'b'); assert.equal(f.spoken[1].rate, 0.86)
})
test('same stage cannot speak twice, either while pending or after completion', async () => {
  const f = outputFixture(), first = f.output.speak('질문', 'q0')
  assert.equal(f.output.speak('질문', 'q0'), first); assert.equal(f.spoken.length, 1)
  f.spoken[0].onend!(); await first; assert.equal(await f.output.speak('질문', 'q0'), true); assert.equal(f.spoken.length, 1)
})
test('an intentional reask may repeat the same sentence with a new stage', async () => {
  const f = outputFixture(); const first = f.output.speak('같은 질문', 'q0:0'); f.spoken[0].onend!(); await first
  const second = f.output.speak('같은 질문', 'q0:1'); assert.equal(f.spoken.length, 2); f.spoken[1].onend!(); await second
})
test('speech errors allow text fallback without hanging the conversation', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0'); f.spoken[0].onerror!()
  assert.equal(await promise, true); assert.match(f.notices[0], /화면의 글/); assert.equal(f.timers.size, 0)
})
test('stop/call end cancels output and invalidates late end events', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0'), late = f.spoken[0].onend!
  f.output.stop(false); assert.equal(await promise, false); late(); assert.equal(f.spoken.length, 1)
  assert.equal(f.spoken[0].onend, null); assert.equal(f.timers.size, 0)
})
test('mute releases the waiting sequence and prevents subsequent audio', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0'); f.mute(); f.output.stop(true)
  assert.equal(await promise, true); assert.equal(await f.output.speak('다음 질문', 'q1'), true); assert.equal(f.spoken.length, 1)
})
test('TTS timeout cleans its timer and gives a text fallback', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0'); [...f.timers.values()][0]()
  assert.equal(await promise, true); assert.match(f.notices[0], /늦어져/); assert.equal(f.timers.size, 0)
})
test('missing or throwing synthesis cannot block text answers', async () => {
  const f = outputFixture(); f.host.speechSynthesis = null
  assert.equal(await f.output.speak('질문', 'q0'), true); assert.match(f.notices[0], /지원하지 않아/)
  const g = outputFixture(); (g.host.speechSynthesis as { speak: () => void }).speak = () => { throw Error('unavailable') }
  assert.equal(await g.output.speak('질문', 'q0'), true); assert.equal(g.timers.size, 0)
})
test('dispose cancels speech without later state updates', async () => {
  const f = outputFixture(), promise = f.output.speak('질문', 'q0'), count = f.states.length
  f.output.dispose(); assert.equal(await promise, false); assert.equal(f.states.length, count); assert.equal(await f.output.speak('다음', 'q1'), false)
})
test('multiple final chunks are joined into one readable answer, empty finals do not submit', () => {
  const f = inputFixture(); f.input.start(); emit(f.instances[0], ' ', true); assert.equal(f.answers.length, 0)
  f.instances[0].onresult!({ resultIndex: 0, results: [Object.assign([{ transcript: '안' }], { isFinal: true }), Object.assign([{ transcript: '아파' }], { isFinal: true })] })
  assert.deepEqual(f.answers, ['안 아파'])
})
