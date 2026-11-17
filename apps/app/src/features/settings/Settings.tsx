import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { koreanTime } from '../../shared/format.ts'
import { Icon } from '../../shared/Icon.tsx'
import { notifyPermission, requestNotifyPermission, type NotifyPermission } from '../../shared/notify.ts'
import { TEXT_SCALES, useSettings } from '../../shared/settings.tsx'
import { TabBar } from '../../shared/ui.tsx'
import { PRIVACY_LINE, speechPrivacy, type RecognitionHost, type SpeechPrivacy } from '../call/speech/recognition.ts'
import { useHome } from '../home/index.ts'

const PERMISSION_VIEW: Record<NotifyPermission, { icon: 'check' | 'alert' | 'bell'; label: string }> = {
  granted: { icon: 'check', label: '알림을 켜 두셨어요' },
  denied: { icon: 'alert', label: '알림이 막혀 있어요. 브라우저 설정에서 허용해 주세요' },
  default: { icon: 'bell', label: '아직 알림을 켜지 않았어요' },
  unsupported: { icon: 'alert', label: '이 브라우저는 알림을 지원하지 않아요' },
}

export function Settings() {
  const { settings, update } = useSettings()
  const { home } = useHome()
  const navigate = useNavigate()
  const [perm, setPerm] = useState<NotifyPermission>(notifyPermission)
  // available()은 일부 크롬(헤드리스 156 등)에서 탭을 멈추게 해서 자동으로 부르지 않는다 — 눌렀을 때만 확인한다
  const [privacy, setPrivacy] = useState<SpeechPrivacy>(settings.speechLocal ? 'local' : 'unknown')
  const [checking, setChecking] = useState(false)
  const checkLocal = () => {
    setChecking(true)
    speechPrivacy(window as unknown as RecognitionHost).then((p) => { setPrivacy(p); update({ speechLocal: p === 'local' }) }).finally(() => setChecking(false))
  }

  return (
    <div className="screen light">
      <header className="ahead"><h1 className="hello serif page-title">설정</h1></header>
      <main className="pad scroll">
        <h2 className="set-title" id="scale-label">글자 크기</h2>
        <div className="scale" role="radiogroup" aria-labelledby="scale-label">
          {TEXT_SCALES.map((s) => (
            <button key={s.key} role="radio" aria-checked={settings.textScale === s.key} aria-label={s.aria}
              className={settings.textScale === s.key ? 'on' : ''} onClick={() => update({ textScale: s.key })}>
              <i style={{ fontSize: `${s.sample}px` }}>가</i>
              <span>{s.label}</span>
            </button>
          ))}
        </div>

        <div className="setrow col">
          <span id="rate-label">말하는 속도</span>
          <div className="seg" role="radiogroup" aria-labelledby="rate-label">
            {[{ v: 0.86, label: '천천히' }, { v: 1, label: '보통' }].map((o) => (
              <button key={o.v} role="radio" aria-checked={settings.rate === o.v} className={settings.rate === o.v ? 'on' : ''}
                onClick={() => update({ rate: o.v })}>{o.label}</button>
            ))}
          </div>
        </div>

        <button className="setrow" role="switch" aria-checked={settings.autoListen} onClick={() => update({ autoListen: !settings.autoListen })}>
          <span>끝나면 자동으로 듣기</span>
          <span className="toggle-wrap">
            <span className="toggle-label">{settings.autoListen ? '켜짐' : '꺼짐'}</span>
            <span className={`toggle${settings.autoListen ? ' on' : ''}`} aria-hidden="true" />
          </span>
        </button>

        <div className="setrow">
          <span>전화 시간</span>
          <span className="set-value">{home ? koreanTime(home.call_time) : '…'}</span>
        </div>
        <p className="hint">전화 시간은 생활지원사님이 정해요.</p>

        <h2 className="set-title">전화 알림</h2>
        <div className="setrow col">
          <span className="set-perm"><Icon name={PERMISSION_VIEW[perm].icon} />{PERMISSION_VIEW[perm].label}</span>
          {perm === 'default' && (
            <button className="btn primary tall wide" onClick={() => requestNotifyPermission().then(setPerm)}>
              <Icon name="bell" /> 전화 알림 받기
            </button>
          )}
        </div>
        <p className="hint">앱을 열어 둔 상태(다른 화면 포함)에서만 알림이 와요. 앱을 완전히 닫으면 전화가 오지 않아요 — 실제 서비스는 전화망 연결이나 푸시 서버가 필요해요.</p>

        <h2 className="set-title">음성 인식</h2>
        <p className="hint"><Icon name={privacy === 'local' ? 'check' : 'alert'} /> {PRIVACY_LINE[privacy]}</p>
        {privacy !== 'local' && (
          <button type="button" className="btn ghost wide" onClick={checkLocal} disabled={checking}>
            <Icon name="mic" /> {checking ? '확인하는 중…' : '이 폰 안에서 인식되는지 확인하기'}
          </button>
        )}

        <div className="demo-foot">
          {settings.residentName && <p className="hint">지금은 {settings.residentName} 어르신 폰이에요.</p>}
          <button className="btn-quiet" onClick={() => { update({ residentId: null, residentName: '' }); navigate('/', { replace: true }) }}>
            <span className="tag-demo">시연용</span> 다른 어르신으로 바꾸기
          </button>
        </div>
      </main>
      <TabBar />
    </div>
  )
}
