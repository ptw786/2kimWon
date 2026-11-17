import { useNavigate } from 'react-router-dom'
import { koreanTime } from '../../shared/format.ts'
import { TEXT_SCALES, useSettings } from '../../shared/settings.tsx'
import { TabBar } from '../../shared/ui.tsx'
import { useHome } from '../home/index.ts'

export function Settings() {
  const { settings, update } = useSettings()
  const { home } = useHome()
  const navigate = useNavigate()

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
