import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'

export type TextScale = 'xs' | 'sm' | 'normal' | 'large' | 'xlarge'
export const TEXT_SCALES: { key: TextScale; label: string; aria: string; sample: number }[] = [
  { key: 'xs', label: '작게', aria: '작게', sample: 20 },
  { key: 'sm', label: '조금 작게', aria: '조금 작게', sample: 22 },
  { key: 'normal', label: '보통', aria: '보통', sample: 24 },
  { key: 'large', label: '크게', aria: '크게', sample: 27 },
  { key: 'xlarge', label: '아주 크게', aria: '아주 크게', sample: 31 },
]

export type Settings = {
  residentId: number | null
  residentName: string
  textScale: TextScale
  rate: number // 0.86 천천히 · 1 보통
  autoListen: boolean
}

const KEY = 'ansimon.app.v2'
const DEFAULTS: Settings = { residentId: null, residentName: '', textScale: 'large', rate: 0.86, autoListen: true }

function load(): Settings {
  try {
    const raw = JSON.parse(localStorage.getItem(KEY) || '{}') as Partial<Settings>
    return {
      residentId: typeof raw.residentId === 'number' ? raw.residentId : null,
      residentName: typeof raw.residentName === 'string' ? raw.residentName : '',
      textScale: TEXT_SCALES.some((s) => s.key === raw.textScale) ? (raw.textScale as TextScale) : DEFAULTS.textScale,
      rate: raw.rate === 1 ? 1 : 0.86,
      autoListen: raw.autoListen !== false,
    }
  } catch {
    return DEFAULTS
  }
}

type Ctx = { settings: Settings; update: (patch: Partial<Settings>) => void }
const SettingsContext = createContext<Ctx | null>(null)

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(load)
  const update = useCallback((patch: Partial<Settings>) => setSettings((s) => ({ ...s, ...patch })), [])
  useEffect(() => {
    try { localStorage.setItem(KEY, JSON.stringify(settings)) } catch { /* 저장 못 해도 이번 화면은 그대로 쓴다 */ }
    document.documentElement.dataset.textScale = settings.textScale
  }, [settings])
  const value = useMemo(() => ({ settings, update }), [settings, update])
  return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>
}

export function useSettings(): Ctx {
  const ctx = useContext(SettingsContext)
  if (!ctx) throw new Error('SettingsProvider missing')
  return ctx
}
