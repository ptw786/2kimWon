import { useEffect, useRef, useState } from 'react'
import { useCall, type Voice } from './CallContext.tsx'
import { useRingtone } from './useRingtone.ts'
import { api } from '../../shared/api.ts'
import { dayLabel, koreanTime } from '../../shared/format.ts'
import { Icon } from '../../shared/Icon.tsx'
import { useSettings } from '../../shared/settings.tsx'
import type { RecordDay } from '../../shared/types.ts'
import { RecordChips } from '../../shared/ui.tsx'
import { useHome } from '../home/index.ts'

const STEPS = ['몸', '식사', '수면', '약', '기분']

export function RingScreen() {
  const call = useCall()
  const { settings } = useSettings()
  const ringtone = useRingtone(call.phase === 'ringing')
  const connecting = call.phase === 'answering'
  return (
    <div className="screen dark" role="dialog" aria-modal="true" aria-labelledby="ring-title">
      <div className="ring">
        <small>{connecting ? '연결하고 있어요…' : '전화가 왔어요'}</small>
        <h1 id="ring-title">안심온 돌봄전화</h1>
        <p>{settings.residentName ? `${settings.residentName} 어르신,` : '어르신,'}<br />오늘도 안녕하세요</p>
        <div className="pulse" aria-hidden="true"><Icon name="heart" filled /></div>
        {ringtone.status === 'blocked' && !connecting && (
          <button className="sound-on" onClick={ringtone.start}><Icon name="bell" /> 벨소리 켜기</button>
        )}
        {call.ringError && <p className="ring-err" role="alert">{call.ringError}</p>}
        <div className="acts">
          <button className="act" onClick={call.decline} disabled={connecting}>
            <span className="circle no"><Icon name="x" stroke={3} /></span>안 받기
          </button>
          <button className="act" onClick={call.answer} disabled={connecting}>
            <span className="circle yes"><Icon name="phone" filled /></span>받기
          </button>
        </div>
      </div>
    </div>
  )
}

function Steps({ index }: { index: number }) {
  return (
    <ol className="stp" aria-label={`다섯 가지 중 ${index}번째 질문`}>
      {STEPS.map((label, i) => {
        const n = i + 1
        const state = n < index ? 'done' : n === index ? 'now' : 'todo'
        return (
          <li key={label} className={state} aria-current={state === 'now' ? 'step' : undefined}>
            <i /><span>{label}</span>
          </li>
        )
      })}
    </ol>
  )
}

const WAVE = [12, 24, 16, 28, 12]

function ListenButton({ voice, onClick }: { voice: Voice; onClick: () => void }) {
  const content: Record<Voice, { label: string; sub: string; aria: string }> = {
    speaking: { label: '안심온이 말하는 중', sub: '끝나면 바로 들을게요', aria: '안심온이 말하는 중이에요. 누르면 멈추고 바로 대답해요' },
    starting: { label: '마이크 켜는 중', sub: '곧 들을게요', aria: '마이크를 켜는 중이에요' },
    listening: { label: '듣고 있어요', sub: '편하게 말씀하세요', aria: '듣고 있어요. 누르면 듣기를 멈춰요' },
    idle: { label: '눌러서 말하기', sub: '마이크가 꺼져 있어요', aria: '눌러서 말로 답하기' },
    sending: { label: '답을 보내는 중', sub: '잠깐만 기다려 주세요', aria: '답을 보내는 중이에요' },
  }
  const c = content[voice]
  return (
    <button className={`listen ${voice}`} onClick={onClick} disabled={voice === 'sending'} aria-label={c.aria}>
      <span className="listen-icon" aria-hidden="true">
        {voice === 'listening'
          ? <span className="wave">{WAVE.map((h, i) => <i key={i} style={{ height: `${h}px`, animationDelay: `${i * 0.12}s` }} />)}</span>
          : <Icon name={voice === 'speaking' ? 'speaker' : 'mic'} />}
      </span>
      <span className="listen-text"><b>{c.label}</b><small>{c.sub}</small></span>
    </button>
  )
}

const HEARD_LABEL = { interim: '들은 말 (듣는 중)', stt: '들은 말', option: '고른 답', text: '쓴 답' }

export function CallScreen() {
  const call = useCall()
  const [confirm, setConfirm] = useState(false)
  const [hangErr, setHangErr] = useState<string | null>(null)
  const [hanging, setHanging] = useState(false)
  const r = call.result
  if (!r) return null
  const finished = r.finished
  const mic = call.micProblem
  const retryable = mic && ['not-allowed', 'audio-capture'].includes(mic.code)

  const placeholder = '말씀하시면 여기에 글로 보여요.'

  const openConfirm = () => { setHangErr(null); setConfirm(true); call.hold(true) }
  const closeConfirm = () => { setConfirm(false); call.hold(false) }
  const doHangup = async () => {
    setHanging(true)
    setHangErr(null)
    try { await call.hangup() } catch (e) { setHangErr((e as Error).message); setHanging(false) }
  }

  return (
    <div className="screen light call">
      <main className="pad scroll call-main">
        <Steps index={r.step.index} />
        {r.empathy && !finished && <p className="empathy">{r.empathy}</p>}
        <h1 className="q" aria-live="polite">{finished ? r.ai_text : (r.question ?? r.ai_text)}</h1>
        {r.safety && (
          <div className="card safety" role="status">
            <Icon name="heart" filled />
            <p>말씀하신 내용을 생활지원사님께 알려 드릴게요. 많이 급하시면 119에 전화해 주세요.</p>
          </div>
        )}
        <section className="voice" aria-label="말로 답하기">
          {mic && !finished ? (
            <>
              <div className="micoff" role="status">
                <Icon name="micOff" />
                <p><b>마이크를 쓸 수 없어요 · 버튼이나 글자로 답해 주세요</b>
                  <small>{mic.message.replace(/\s*버튼이나 글자로 답해 주세요\.?$/, '')}</small></p>
              </div>
              {retryable && <button className="btn ghost wide tall" onClick={call.retryMic}><Icon name="mic" /> 마이크 다시 연결</button>}
            </>
          ) : (
            <ListenButton voice={call.voice} onClick={call.toggleMic} />
          )}
          {!finished && (!mic || call.heard) && (
            <div className={`heard${call.heard?.kind === 'interim' ? ' interim' : ''}`}>
              <small><Icon name={call.heard?.kind === 'option' ? 'hand' : call.heard?.kind === 'text' ? 'keyboard' : 'mic'} />{call.heard ? HEARD_LABEL[call.heard.kind] : '들은 말'}</small>
              {call.heard ? <p>“{call.heard.text}”</p> : <p className="muted">{placeholder}</p>}
            </div>
          )}
        </section>
        {!finished && r.options.length > 0 && (
          <div className="opt" role="group" aria-label="골라서 답하기">
            {r.options.map((o) => (
              <button key={o} className={call.selected === o ? 'on' : ''} aria-pressed={call.selected === o}
                disabled={call.voice === 'sending'} onClick={() => call.choose(o)}>
                <i aria-hidden="true">{call.selected === o && <Icon name="check" stroke={3.2} />}</i>{o}
              </button>
            ))}
          </div>
        )}
        {call.error && !call.textOpen && (
          <div className="card soft" role="alert">
            <p className="card-text">{call.error}</p>
            <button className="btn primary" onClick={call.retry}>다시 보내기</button>
          </div>
        )}
        {(call.sttHint || call.ttsNotice) && <p className="hint">{call.sttHint || call.ttsNotice}</p>}
      </main>

      {!finished && (
        <footer className="dock">
          <button className="btn-text" onClick={() => call.setTextOpen(true)}><Icon name="keyboard" />글자로 답하기</button>
          <button className="btn-hang" onClick={openConfirm}><Icon name="phone" filled />끊기</button>
        </footer>
      )}

      {call.textOpen && <TextSheet />}
      {confirm && (
        <div className="backdrop center" role="alertdialog" aria-modal="true" aria-labelledby="hang-title">
          <div className="dialog">
            <h2 id="hang-title">전화를 끊을까요?</h2>
            <p>끊으시면 남은 질문은 다음 전화 때 여쭐게요.</p>
            {hangErr && <p className="err-text" role="alert">{hangErr}</p>}
            <button className="btn primary wide tall" onClick={closeConfirm} disabled={hanging}>계속 이야기하기</button>
            <button className="btn danger wide tall" onClick={doHangup} disabled={hanging}>
              <Icon name="phone" filled />{hanging ? '끊는 중…' : hangErr ? '다시 끊기' : '끊기'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function TextSheet() {
  const call = useCall()
  const ref = useRef<HTMLTextAreaElement>(null)
  useEffect(() => { ref.current?.focus() }, [])
  const sending = call.voice === 'sending'
  return (
    <div className="backdrop" role="dialog" aria-modal="true" aria-labelledby="text-title">
      <div className="sheet">
        <h2 id="text-title">글자로 답하기</h2>
        {call.result?.question && <p className="sheet-q">{call.result.question}</p>}
        <textarea ref={ref} value={call.draft} maxLength={500} rows={3} placeholder="여기에 적어 주세요"
          aria-label="답을 적는 칸" onChange={(e) => call.setDraft(e.target.value)} />
        {call.error && <p className="err-text" role="alert">{call.error} 적으신 글은 그대로 있어요.</p>}
        <div className="sheet-row">
          <button className="btn ghost tall" onClick={() => call.setTextOpen(false)}>닫기</button>
          <button className="btn primary tall" disabled={!call.draft.trim() || sending} onClick={call.sendText}>
            {sending ? '보내는 중…' : call.error ? '다시 보내기' : '보내기'}
          </button>
        </div>
      </div>
    </div>
  )
}

export function DoneScreen() {
  const call = useCall()
  const { settings } = useSettings()
  const { home } = useHome()
  const [today, setToday] = useState<RecordDay | null>(null)
  const id = settings.residentId

  // 오늘 말씀을 '내 기록'과 같은 칩으로 보여 준다(통화가 끝나면 서버가 바로 정리해 둔다).
  useEffect(() => {
    if (id === null) return
    let live = true
    api.records(id).then((days) => {
      const first = days[0]
      if (live && first && dayLabel(first.date) === '오늘' && first.chips.length > 0) setToday(first)
    }).catch(() => { /* 요약 없이도 화면은 그대로 */ })
    return () => { live = false }
  }, [id])

  return (
    <div className="screen light">
      <main className="pad scroll done-main">
        <div className="done-body">
          <div className="done-heart" aria-hidden="true"><Icon name="heart" filled /></div>
          <h1 className="hello serif">오늘도 고맙습니다</h1>
          <p className="card-text">{settings.residentName ? `${settings.residentName} 어르신, ` : ''}오늘 이야기 잘 들었어요.</p>
          {today && (
            <section className="done-sum" aria-label="오늘 말씀하신 것">
              <small>오늘 말씀하신 것</small>
              <RecordChips chips={today.chips} />
              <p className="hint">내 기록에 남겨 두었어요</p>
            </section>
          )}
          <section className="next" aria-label="다음 안심온 전화">
            <small>다음 안심온 전화 · 내일</small><b className="next-time">{home ? koreanTime(home.call_time) : '같은 시간'}</b>
          </section>
          <button className="callnow" onClick={call.finish}>처음 화면으로</button>
        </div>
      </main>
    </div>
  )
}
