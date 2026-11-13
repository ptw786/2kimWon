import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, friendly } from '../../shared/api.ts'
import { useSettings } from '../../shared/settings.tsx'
import type { ResidentRef } from '../../shared/types.ts'
import { ErrorCard, Logo } from '../../shared/ui.tsx'

/** 시연용: 처음 켤 때 누구 폰인지 고른다. 실제로는 QR(/r/코드)로 열면 바로 정해진다. */
export function Picker() {
  const { update } = useSettings()
  const [list, setList] = useState<ResidentRef[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tries, setTries] = useState(0)

  useEffect(() => {
    let live = true
    setError(null)
    api.residents().then((r) => { if (live) setList(r) }).catch((e) => { if (live) setError(friendly(e)) })
    return () => { live = false }
  }, [tries])

  return (
    <div className="screen light">
      <header className="ahead"><Logo /><span className="tag-demo">시연용</span></header>
      <main className="pad scroll">
        <h1 className="hello serif">어느 어르신<br />폰인가요?</h1>
        <p className="card-text muted">시연용 화면이에요. 실제로는 생활지원사님이 드린 QR로 열면 바로 정해져요.</p>
        {error && <ErrorCard message={error} onRetry={() => setTries((t) => t + 1)} />}
        {!error && list === null && <p className="card-text muted">불러오고 있어요…</p>}
        <div className="pick">
          {list?.map((r) => (
            <button key={r.id} onClick={() => update({ residentId: r.id, residentName: r.name })}>
              <b>{r.name} 어르신</b><span className="code-chip">{r.code}</span>
            </button>
          ))}
        </div>
      </main>
    </div>
  )
}

/** QR로 연 주소 /r/:code → 어르신을 찾아 저장하고 홈으로 간다. */
export function ByCode() {
  const { code = '' } = useParams()
  const { update } = useSettings()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [tries, setTries] = useState(0)

  useEffect(() => {
    let live = true
    setError(null)
    api.byCode(code).then((r) => {
      if (!live) return
      update({ residentId: r.id, residentName: r.name })
      navigate('/', { replace: true })
    }).catch((e) => {
      if (!live) return
      setError(e instanceof ApiError && e.status === 404 ? `'${code}' 코드의 어르신을 찾지 못했어요.` : friendly(e))
    })
    return () => { live = false }
  }, [code, tries, update, navigate])

  return (
    <div className="screen light">
      <header className="ahead"><Logo /></header>
      <main className="pad scroll">
        {!error && <p className="card-text">어르신을 찾고 있어요…</p>}
        {error && (
          <>
            <ErrorCard message={error} onRetry={() => setTries((t) => t + 1)} />
            <button className="btn ghost wide" onClick={() => navigate('/', { replace: true })}>직접 고르기</button>
          </>
        )}
      </main>
    </div>
  )
}
