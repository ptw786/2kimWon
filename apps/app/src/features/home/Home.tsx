import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, friendly } from '../../shared/api.ts'
import homeNight from '../../shared/assets/home-night.jpg'
import { koreanTime } from '../../shared/format.ts'
import { Icon } from '../../shared/Icon.tsx'
import { useSettings } from '../../shared/settings.tsx'
import type { RecordDay } from '../../shared/types.ts'
import { ErrorCard, TabBar } from '../../shared/ui.tsx'
import { useCall } from '../call/index.ts'
import { useHome } from './useHome.ts'

/** "식사를 잘 못 하셨어요" → "식사를 잘 못 하셨다고 하셔서", 짧은 칩("식사 걱정")이면 → "식사 걱정 이야기를 하셔서" */
const toBecause = (label: string) => (/어요$/.test(label) ? label.replace(/어요$/, '다고 하셔서') : `${label} 이야기를 하셔서`)

/** 말풍선: 지난 통화에서 걱정된 말을 이어받는다. 없으면 오늘 전화 시간을 알려 준다. */
function opener(records: RecordDay[] | null, todayDone: boolean, callTime: string | null) {
  const when = callTime ? koreanTime(callTime) : '정해진 시간'
  if (todayDone) return { small: '오늘 통화를 마쳤어요', text: '오늘 이야기 잘 들었어요. 편히 쉬세요.' }
  const last = records?.find((r) => r.chips.some((c) => c.tone === 'watch' && !c.label.includes('알렸')))
  const worry = last?.chips.find((c) => c.tone === 'watch' && !c.label.includes('알렸'))
  if (last && worry) {
    const [, m, d] = last.date.split('-').map(Number)
    return { small: `지난 통화 · ${m}월 ${d}일`, text: `지난번에 ${toBecause(worry.label)} 마음이 쓰였어요. 오늘은 어떠세요?` }
  }
  return { small: '안심온이 기다리고 있어요', text: `오늘 하루는 어떠세요? ${when}에 전화드릴게요.` }
}

function nowLabel() {
  const d = new Date()
  return koreanTime(`${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`)
}

export function Home() {
  const { settings, update } = useSettings()
  const call = useCall()
  const { home, error, reload } = useHome()
  const [records, setRecords] = useState<RecordDay[] | null>(null)
  const [ringing, setRinging] = useState(false)
  const [ringErr, setRingErr] = useState<string | null>(null)
  const [helpOpen, setHelpOpen] = useState(false)
  const name = home?.name || settings.residentName
  const id = settings.residentId

  useEffect(() => {
    if (id === null) return
    let live = true
    api.records(id).then((r) => { if (live) setRecords(r) }).catch(() => { if (live) setRecords([]) })
    return () => { live = false }
  }, [id, home])

  const todayDone = home ? !['not_called', 'ringing', 'in_progress'].includes(home.today.status) : false
  const say = opener(records, todayDone, home?.call_time ?? null)

  const ringMe = async () => {
    setHelpOpen(false)
    setRinging(true)
    setRingErr(null)
    try { await call.ringMe() } catch (e) { setRingErr(friendly(e)) } finally { setRinging(false) }
  }

  return (
    <div className="screen lv">
      <div className="scroll">
        <div className="lv-scene">
          <img src={homeNight} alt="스탠드 불이 켜진 저녁 거실. 소파와 탁자 위 찻잔 두 개." />
          <div className="lv-head">
            <h1 className="lv-place">
              <b>{name ? `${name} 어르신 댁` : '어르신 댁'}</b>
              <small><i className="lv-dot" aria-hidden="true" />{nowLabel()}</small>
            </h1>
            <button type="button" className="lv-help" onClick={() => setHelpOpen(true)}>
              <Icon name="hand" /> 도움 받기
            </button>
          </div>
          {call.notice ? (
            <div className="lv-say" role="status">
              <small><Icon name="bell" /> 안심온 알림
                <button type="button" className="lv-ok" onClick={call.dismissNotice}>알겠어요</button>
              </small>
              {call.notice}
            </div>
          ) : (
            <p className="lv-say">
              <small>{say.small}</small>
              {say.text}
            </p>
          )}
          {todayDone ? (
            <p className="lv-when"><Icon name="bell" /> 내일 {home ? koreanTime(home.call_time) : ''}에 전화드려요</p>
          ) : (
            <button type="button" className="lv-tag" onClick={ringMe} disabled={ringing}>
              <Icon name="phone" filled /> {ringing ? '거는 중…' : '지금 전화 받기'}
            </button>
          )}
        </div>

        <section className="lv-panel">
          {error && <ErrorCard message={error} onRetry={reload} />}

          <p className="lv-title">어떻게 답하실래요?</p>
          <div className="lv-seg" role="radiogroup" aria-label="답하는 방법">
            <button type="button" role="radio" aria-checked={settings.autoListen} onClick={() => update({ autoListen: true })}>
              <Icon name="mic" /> 말로 하기
            </button>
            <button type="button" role="radio" aria-checked={!settings.autoListen} onClick={() => update({ autoListen: false })}>
              <Icon name="hand" /> 버튼 누르기
            </button>
          </div>

          <button type="button" className="lv-btn" onClick={ringMe} disabled={ringing}>
            <Icon name="phone" filled /> {ringing ? '전화를 거는 중…' : '안심온과 통화하기'}
          </button>
          <p className="demo-cap"><span className="tag-demo">시연용</span> 누르면 바로 전화가 와요</p>
          {ringErr && <p className="err-text" role="alert">{ringErr}</p>}

          <Link to="/records" className="lv-sum" aria-label={`${home ? `이번 주 ${home.week_count}번 통화 · ` : ''}지난 통화 보기`}>
            <span>{home && <>이번 주 <b>{home.week_count}번</b> 통화<span className="lv-sum-more"> · </span></>}<span className={home ? 'lv-sum-more' : ''}>지난 통화 보기</span></span>
            <Icon name="chevron" />
          </Link>
        </section>
      </div>
      <TabBar />

      {helpOpen && (
        <div className="backdrop" role="dialog" aria-modal="true" aria-labelledby="help-title" onClick={() => setHelpOpen(false)}>
          <div className="sheet" onClick={(e) => e.stopPropagation()}>
            <h2 id="help-title">도움이 필요하세요?</h2>
            <p className="sheet-q">위급하시면 바로 119에 전화하세요. 안심온은 119에 자동으로 신고하지 않아요.</p>
            <a className="btn danger tall wide call119" href="tel:119"><Icon name="phone" filled /> 119에 전화하기</a>
            <button type="button" className="btn primary tall wide" onClick={ringMe}>
              <Icon name="heart" filled /> 안심온과 지금 이야기하기
            </button>
            <button type="button" className="btn ghost wide" onClick={() => setHelpOpen(false)}>닫기</button>
          </div>
        </div>
      )}
    </div>
  )
}
