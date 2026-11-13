import { useEffect, useState } from 'react'
import { api, friendly } from '../../shared/api.ts'
import { useSettings } from '../../shared/settings.tsx'
import type { HomeData } from '../../shared/types.ts'
import { useCall } from '../call/index.ts'

/** 홈 요약(이름·전화 시간). 통화가 끝날 때마다(homeVersion) 다시 부른다. */
export function useHome() {
  const { settings } = useSettings()
  const { homeVersion } = useCall()
  const [home, setHome] = useState<HomeData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tries, setTries] = useState(0)
  const id = settings.residentId
  useEffect(() => {
    if (id === null) return
    let live = true
    setError(null)
    api.home(id).then((h) => { if (live) setHome(h) }).catch((e) => { if (live) setError(friendly(e)) })
    return () => { live = false }
  }, [id, homeVersion, tries])
  return { home, error, reload: () => setTries((t) => t + 1) }
}
