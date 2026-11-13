import { useEffect, useState } from 'react'
import { api, friendly } from '../../shared/api.ts'
import { useCall } from '../call/index.ts'
import { clockLabel, dayLabel } from '../../shared/format.ts'
import { useSettings } from '../../shared/settings.tsx'
import type { RecordDay } from '../../shared/types.ts'
import { ErrorCard, RecordChips, TabBar } from '../../shared/ui.tsx'

export function Records() {
  const { settings } = useSettings()
  const { homeVersion } = useCall()
  const [days, setDays] = useState<RecordDay[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tries, setTries] = useState(0)
  const id = settings.residentId

  useEffect(() => {
    if (id === null) return
    let live = true
    setError(null)
    api.records(id).then((d) => { if (live) setDays(d) }).catch((e) => { if (live) setError(friendly(e)) })
    return () => { live = false }
  }, [id, homeVersion, tries])

  return (
    <div className="screen light">
      <header className="ahead"><h1 className="hello serif page-title">내 기록</h1></header>
      <main className="pad scroll rec-list">
        {error && <ErrorCard message={error} onRetry={() => setTries((t) => t + 1)} />}
        {!error && days === null && <p className="card-text muted">기록을 불러오고 있어요…</p>}
        {days?.length === 0 && <p className="card-text muted">아직 기록이 없어요.</p>}
        {days?.map((d) => (
          <article className="rec" key={d.date}>
            <b>{dayLabel(d.date)}</b>
            <small>{d.time ? `${clockLabel(d.time)}${d.minutes ? ` · ${d.minutes}분` : ''}` : d.status_label}</small>
            <RecordChips chips={d.chips} />
          </article>
        ))}
      </main>
      <TabBar />
    </div>
  )
}
