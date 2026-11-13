// ansimon-fullstack/frontend/src/hooks/useRingtone.js를 옮겼다.
// 한 벨 화면에 AudioContext 하나, 작은 사인파 두 개(440+480Hz, 전화 벨 소리), 박자 타이머 하나.
// 브라우저가 소리를 막으면(사용자가 아직 화면을 누르지 않음) status가 'blocked' → 화면에 '벨소리 켜기'를 보인다.
// 진동(navigator.vibrate)이 되는 폰이면 벨과 같은 박자로 함께 떤다.
import { useCallback, useEffect, useRef, useState } from 'react'

export type RingStatus = 'idle' | 'ringing' | 'blocked' | 'unavailable'

type Session = { context: AudioContext; gain: GainNode | null; oscillators: OscillatorNode[]; timer: number | null }

const VIBRATE = [800, 400, 800]

function vibrate(pattern: number | number[]) {
  try { navigator.vibrate?.(pattern) } catch { /* 진동 없음 */ }
}

export function useRingtone(enabled: boolean) {
  const session = useRef<Session | null>(null)
  const alive = useRef(false)
  const buzz = useRef<number | null>(null)
  const [status, setStatus] = useState<RingStatus>('idle')

  const dispose = useCallback(() => {
    if (buzz.current !== null) { clearInterval(buzz.current); buzz.current = null; vibrate(0) }
    const current = session.current
    session.current = null
    if (!current) return
    if (current.timer !== null) clearInterval(current.timer)
    current.context.onstatechange = null
    if (current.gain) { current.gain.gain.cancelScheduledValues(0); current.gain.gain.value = 0 }
    for (const node of current.oscillators) { try { node.stop() } catch { /* stopped */ } node.disconnect() }
    current.gain?.disconnect()
    if (current.context.state !== 'closed') current.context.close().catch(() => {})
  }, [])

  const stop = useCallback(() => { dispose(); if (alive.current) setStatus('idle') }, [dispose])

  const start = useCallback(() => {
    if (!alive.current || !enabled) return
    if (buzz.current === null && typeof navigator.vibrate === 'function') {
      vibrate(VIBRATE)
      buzz.current = window.setInterval(() => vibrate(VIBRATE), 4000)
    }
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctx) { setStatus('unavailable'); return }
    let current = session.current
    try {
      if (!current) {
        const context = new Ctx()
        const created: Session = { context, gain: null, oscillators: [], timer: null }
        current = created
        session.current = created
        const gain = context.createGain(); created.gain = gain
        gain.gain.value = 0; gain.connect(context.destination)
        for (const frequency of [440, 480]) {
          const oscillator = context.createOscillator(); created.oscillators.push(oscillator)
          oscillator.type = 'sine'; oscillator.frequency.value = frequency
          oscillator.connect(gain); oscillator.start()
        }
      }
      const s = current
      const update = () => {
        if (!alive.current || session.current !== s) return
        if (s.context.state !== 'running') {
          if (s.timer !== null) clearInterval(s.timer)
          s.timer = null
          setStatus('blocked'); return
        }
        if (s.timer === null) {
          const pulse = () => {
            const time = s.context.currentTime, gain = s.gain!.gain
            gain.cancelScheduledValues(time); gain.setValueAtTime(0, time)
            for (const offset of [0, 1.2]) {
              gain.setValueAtTime(0, time + offset)
              gain.linearRampToValueAtTime(0.045, time + offset + 0.025)
              gain.setValueAtTime(0.045, time + offset + 0.75)
              gain.linearRampToValueAtTime(0, time + offset + 0.8)
            }
          }
          pulse(); s.timer = window.setInterval(pulse, 4000)
        }
        setStatus('ringing')
      }
      s.context.onstatechange = update
      // Do not await resume: autoplay policy may leave its promise pending forever.
      if (s.context.state !== 'running') s.context.resume().then(update).catch(() => {
        if (alive.current && session.current === s) setStatus('blocked')
      })
      update()
    } catch {
      dispose()
      if (alive.current) setStatus('unavailable')
    }
  }, [enabled, dispose])

  useEffect(() => { alive.current = true; return () => { alive.current = false; dispose() } }, [dispose])
  useEffect(() => {
    if (enabled) start()
    else stop()
    return dispose
  }, [enabled, start, stop, dispose])

  return { status, start, stop }
}
