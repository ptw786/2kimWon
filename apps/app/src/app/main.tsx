import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { App } from './App.tsx'
import { DeviceFrame, isInDevice, shouldFrame } from './DeviceFrame.tsx'
import './styles.css'

// 넓은 화면: 바깥은 폰 프레임만 그리고, 앱은 프레임 안 iframe(실제 폰 크기)에서 돈다 — 통화·벨소리가 두 번 돌지 않게.
if (isInDevice()) document.documentElement.classList.add('in-device')
const framed = shouldFrame()
if (framed) document.documentElement.classList.add('framed')
createRoot(document.getElementById('root')!).render(<StrictMode>{framed ? <DeviceFrame /> : <App />}</StrictMode>)

// 서비스 워커는 배포용 빌드에서만 등록한다(개발 중 캐시 혼란 방지). /api는 항상 네트워크로만 간다(public/sw.js).
if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => { navigator.serviceWorker.register('/sw.js').catch(() => {}) })
}
