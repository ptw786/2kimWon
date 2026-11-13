import { useEffect, useRef, useState } from 'react'

/**
 * 넓은 화면(PC)에서 직접 열면 실제 휴대폰 모양(테두리 · 다이내믹 아일랜드 · 상태바 · 홈 바)을 그리고,
 * 그 안에 앱을 **실제 폰 크기(393×852)** 의 iframe으로 띄운 뒤 프레임 전체를 화면에 맞게 줄인다.
 * 그래서 앱 안의 레이아웃(높이 기준 배치, 작은 화면 규칙)이 실제 폰과 똑같이 계산된다.
 * 실제 폰, 그리고 웹 소개·실시간 화면의 iframe 안에서는 그리지 않는다(바깥이 이미 프레임을 그림).
 * 강제로 끄기: 주소 끝에 ?frame=0
 * 출처: 한벗 apps/web/src/app/DeviceFrame.tsx (넓은 화면에서 폰 프레임, 폰에서는 전체 화면)
 */
const SCREEN_W = 393
const SCREEN_H = 852
const BEZEL = 11

const params = () => new URLSearchParams(window.location.search)

/** 이 창이 폰 프레임 안의 앱인가 (상태바·홈 바 자리를 비워야 함) */
export function isInDevice() {
  return typeof window !== 'undefined' && params().get('device') === '1'
}

export function shouldFrame() {
  if (typeof window === 'undefined') return false
  let inIframe = true
  try { inIframe = window.self !== window.top } catch { inIframe = true }
  return !inIframe && params().get('frame') !== '0' && window.matchMedia('(min-width: 600px)').matches
}

function clock() {
  const d = new Date()
  return `${d.getHours() % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`
}

function fitScale() {
  return Math.min(1, (window.innerHeight - 70) / (SCREEN_H + BEZEL * 2))
}

function StatusIcons() {
  return (
    <span className="df-icons" aria-hidden="true">
      <svg viewBox="0 0 18 12" width="18" height="12"><rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" /><rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" /></svg>
      <svg viewBox="0 0 16 12" width="16" height="12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.6 6.6 0 0 1 9.2 0l-1.4 1.4a4.6 4.6 0 0 0-6.4 0zM1.2 4.6a9.8 9.8 0 0 1 13.6 0l-1.4 1.4a7.8 7.8 0 0 0-10.8 0z" /></svg>
      <svg viewBox="0 0 27 12" width="27" height="12"><rect x=".5" y=".5" width="23" height="11" rx="3.5" fill="none" stroke="currentColor" opacity=".45" /><rect x="2.5" y="2.5" width="17" height="7" rx="2" /><path d="M25 4v4a2 2 0 0 0 0-4z" opacity=".45" /></svg>
    </span>
  )
}

export function DeviceFrame() {
  const frame = useRef<HTMLIFrameElement>(null)
  const [scale, setScale] = useState(fitScale)
  const [time, setTime] = useState(clock)
  const [light, setLight] = useState(false)
  const src = (() => {
    const q = params(); q.set('frame', '0'); q.set('device', '1')
    return `${window.location.pathname}?${q.toString()}${window.location.hash}`
  })()

  useEffect(() => {
    const onResize = () => {
      if (!shouldFrame()) { window.location.reload(); return } // 창을 폰 크기로 줄이면 전체 화면 앱으로
      setScale(fitScale())
    }
    window.addEventListener('resize', onResize)
    const clockTimer = window.setInterval(() => setTime(clock()), 15000)
    // 같은 출처라 안쪽 화면이 밝은지 읽어서 상태바 글자색을 맞춘다.
    const toneTimer = window.setInterval(() => {
      try { setLight(Boolean(frame.current?.contentDocument?.querySelector('.screen.light'))) } catch { /* 무시 */ }
    }, 400)
    return () => { window.removeEventListener('resize', onResize); window.clearInterval(clockTimer); window.clearInterval(toneTimer) }
  }, [])

  const outerW = (SCREEN_W + BEZEL * 2) * scale
  const outerH = (SCREEN_H + BEZEL * 2) * scale
  return (
    <div className="df-stage">
      <div className="df-fit" style={{ width: outerW, height: outerH }}>
        <div className="df-phone" style={{ transform: `scale(${scale})` }}>
          <div className={`df-screen ${light ? 'tone-light' : ''}`}>
            <iframe ref={frame} className="df-app" src={src} title="안심온 어르신 앱" allow="microphone; autoplay" />
            <div className="df-status"><span className="df-time">{time}</span><i className="df-island" /><StatusIcons /></div>
            <i className="df-home" aria-hidden="true" />
          </div>
        </div>
      </div>
      <p className="df-cap">안심온 어르신 앱 · 실제 폰에서는 화면 전체로 열려요</p>
    </div>
  )
}
