import { NavLink } from 'react-router-dom'
import { Icon } from './Icon.tsx'
import type { RecordDay } from './types.ts'

export function Logo() {
  return <span className="logo"><i><Icon name="heart" filled size="0.8em" /></i>안심온</span>
}

export function TabBar() {
  const tabs = [
    { to: '/', label: '거실', icon: 'home' as const },
    { to: '/records', label: '내 기록', icon: 'list' as const },
    { to: '/settings', label: '설정', icon: 'gear' as const },
  ]
  return (
    <nav className="tabbar" aria-label="아래 메뉴">
      {tabs.map((t) => (
        <NavLink key={t.to} to={t.to} end className={({ isActive }) => (isActive ? 'on' : '')}>
          <em><Icon name={t.icon} /></em>{t.label}
        </NavLink>
      ))}
    </nav>
  )
}

export function ErrorCard({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="card soft" role="alert">
      <p className="card-text">{message}</p>
      <button className="btn primary" onClick={onRetry}>다시 불러오기</button>
    </div>
  )
}

/** 하루 기록 칩: 걱정된 것만 보여 주고, 모두 괜찮으면 한 줄로. 걱정 칩은 놀라지 않게 버터색 + 하트 + 쉬운 말. */
export function RecordChips({ chips }: { chips: RecordDay['chips'] }) {
  if (chips.length === 0) return null
  const watch = chips.filter((c) => c.tone === 'watch')
  if (watch.length === 0) {
    return <p className="rk-all"><Icon name="check" stroke={3} />모두 괜찮으셨어요</p>
  }
  return (
    <ul className="rk-row">
      {watch.map((c) => (
        <li key={c.label} className="rk-wt"><Icon name={c.label.includes('알렸') ? 'bell' : 'heart'} />{c.label}</li>
      ))}
    </ul>
  )
}
