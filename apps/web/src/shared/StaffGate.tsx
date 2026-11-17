// 생활지원사 로그인(PIN)과 안전 신호 알림. 서버가 401을 주면 로그인 화면, 안전 신호가 오면 맨 위 알림 막대.
import { useEffect, useRef, useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { api, errMsg, setToken } from './api';
import type { Alert } from './types';

export function LoginScreen() {
  const [pin, setPin] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!pin.trim()) return;
    setBusy(true);
    setError('');
    try {
      const r = await api.post<{ token: string }>('/staff/login', { pin: pin.trim() });
      setToken(r.token);
    } catch (err) {
      setError(errMsg(err));
      setBusy(false);
    }
  }
  return (
    <main className="login">
      <form className="login-card" onSubmit={submit}>
        <Link to="/" className="logo" aria-label="안심온 소개로"><i aria-hidden>♥</i>안심온</Link>
        <h1>생활지원사 로그인</h1>
        <p>어르신 정보가 있는 화면이라 비밀번호가 필요해요.</p>
        <label htmlFor="pin">비밀번호(PIN)</label>
        <input id="pin" type="password" inputMode="numeric" autoComplete="current-password" value={pin} onChange={(e) => setPin(e.target.value)} autoFocus />
        {error && <p className="err" role="alert">{error}</p>}
        <button type="submit" className="btn p block" disabled={busy || !pin.trim()}>{busy ? '확인하는 중…' : '들어가기'}</button>
        <small>시연: 서버를 켤 때 로그에 나오는 6자리예요. 정해 두려면 ANSIMON_STAFF_PIN을 쓰세요.</small>
      </form>
    </main>
  );
}

/** 짧은 알림음 두 번 (브라우저가 소리를 막으면 조용히 넘어간다) */
function beep() {
  try {
    const Ctx = window.AudioContext || (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Ctx) return;
    const ctx = new Ctx();
    [0, 0.35].forEach((t) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.frequency.value = 880;
      g.gain.setValueAtTime(0.0001, ctx.currentTime + t);
      g.gain.exponentialRampToValueAtTime(0.25, ctx.currentTime + t + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, ctx.currentTime + t + 0.25);
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + t);
      o.stop(ctx.currentTime + t + 0.3);
    });
    window.setTimeout(() => void ctx.close(), 1000);
  } catch {
    /* 소리 없이 화면 알림만 */
  }
}

const canNotify = () => typeof Notification !== 'undefined';

/** 오늘 확인하지 않은 안전 신호. 새 신호가 오면 소리·브라우저 알림(허용했을 때)·탭 제목으로 알린다. */
export function AlertBar({ alerts }: { alerts: Alert[] }) {
  const seen = useRef<number | null>(null);
  const [hiddenUpTo, setHiddenUpTo] = useState(0);
  const [perm, setPerm] = useState(() => (canNotify() ? Notification.permission : 'denied'));
  const newest = alerts[0];

  useEffect(() => {
    const top = newest?.id ?? 0;
    if (seen.current === null) {
      seen.current = top; // 처음 열었을 때 이미 있던 것은 소리 없이 보여만 준다
      return;
    }
    if (top > seen.current && newest) {
      seen.current = top;
      beep();
      if (canNotify() && Notification.permission === 'granted') {
        try {
          new Notification(`즉시 확인 · ${newest.resident_name} 어르신`, { body: `${newest.category} — “${newest.quote}”`, tag: `ansimon-${newest.id}` });
        } catch {
          /* 알림 실패는 화면 막대로 충분 */
        }
      }
    }
  }, [newest]);

  useEffect(() => {
    const base = document.title.replace(/^\(⚠ \d+\) /, '');
    document.title = alerts.length ? `(⚠ ${alerts.length}) ${base}` : base;
  }, [alerts.length]);

  if (!newest || newest.id <= hiddenUpTo) return null;
  const href = newest.live ? `/staff/live?call=${newest.call_id}` : `/staff/calls/${newest.call_id}`;
  return (
    <div className="alert-bar" role="alert">
      <span className="ic" aria-hidden>⚠</span>
      <div className="txt">
        <b>즉시 확인 · {newest.resident_name} 어르신{newest.live ? ' · 지금 통화 중' : ''}</b>
        <span>{newest.category} — “{newest.quote}”{alerts.length > 1 ? ` · 확인 안 한 안전 신호 ${alerts.length}건` : ''}</span>
      </div>
      <Link to={href} className="btn w">{newest.live ? '통화 보기' : '통화 상세'} ›</Link>
      {canNotify() && perm === 'default' && (
        <button type="button" className="btn ghost-w" onClick={() => void Notification.requestPermission().then(setPerm)}>창 알림 켜기</button>
      )}
      <button type="button" className="btn ghost-w" onClick={() => setHiddenUpTo(newest.id)} title="새 안전 신호가 오면 다시 떠요">잠시 숨기기</button>
    </div>
  );
}
