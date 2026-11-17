// 실제 아이폰 모양 프레임 — 어르신 앱의 DeviceFrame(apps/app/src/app/DeviceFrame.tsx)과 같은 치수·모양.
// 앱은 실제 폰 크기(393×852) iframe으로 띄우고 프레임 전체를 width에 맞게 줄인다(앱 레이아웃이 실제 폰과 같게 계산됨).
// ?device=1을 붙이면 앱이 상태바(47px)·홈 표시줄 자리를 비운다. 상태바는 이 프레임이 위에 그린다.
// 다른 출처(5181) iframe이라 안쪽 화면 밝기를 읽을 수 없어, 상태바 글자는 difference 합성으로 바탕과 반대색이 되게 한다.
import { useEffect, useRef, useState, type ReactNode } from 'react';

export const SCREEN_W = 393;
export const SCREEN_H = 852;
const BEZEL = 11;
export const OUTER_W = SCREEN_W + BEZEL * 2;
export const OUTER_H = SCREEN_H + BEZEL * 2;

/** 폰 바깥 높이(px)에 맞는 폭 */
export const widthForHeight = (h: number) => Math.round((h * OUTER_W) / OUTER_H);

function clock() {
  const d = new Date();
  return `${d.getHours() % 12 || 12}:${String(d.getMinutes()).padStart(2, '0')}`;
}

function StatusIcons() {
  return (
    <span className="pf-icons" aria-hidden="true">
      <svg viewBox="0 0 18 12" width="18" height="12"><rect x="0" y="8" width="3" height="4" rx="1" /><rect x="5" y="5.5" width="3" height="6.5" rx="1" /><rect x="10" y="3" width="3" height="9" rx="1" /><rect x="15" y="0" width="3" height="12" rx="1" /></svg>
      <svg viewBox="0 0 16 12" width="16" height="12"><path d="M8 11.5 5.6 9a3.4 3.4 0 0 1 4.8 0zM3.4 6.8a6.6 6.6 0 0 1 9.2 0l-1.4 1.4a4.6 4.6 0 0 0-6.4 0zM1.2 4.6a9.8 9.8 0 0 1 13.6 0l-1.4 1.4a7.8 7.8 0 0 0-10.8 0z" /></svg>
      <svg viewBox="0 0 27 12" width="27" height="12"><rect x=".5" y=".5" width="23" height="11" rx="3.5" fill="none" stroke="currentColor" opacity=".45" /><rect x="2.5" y="2.5" width="17" height="7" rx="2" /><path d="M25 4v4a2 2 0 0 0 0-4z" opacity=".45" /></svg>
    </span>
  );
}

/**
 * src가 있으면 앱 iframe을 띄운다. iframe이 화면에 들어오고(load) 그려질 때까지는 fallback(정지 화면)을 보여 준다
 * → 앱이 꺼졌거나 늦게 떠도 빈 상자가 보이지 않는다.
 */
export function PhoneFrame({ width, src, title = '어르신 앱', fallback }: { width: number; src?: string | null; title?: string; fallback?: ReactNode }) {
  const s = width / OUTER_W;
  const [time, setTime] = useState(clock);
  useEffect(() => {
    const t = window.setInterval(() => setTime(clock()), 15000);
    return () => window.clearInterval(t);
  }, []);

  return (
    <div className="pf-fit" style={{ width, height: Math.round(OUTER_H * s) }}>
      <div className="pf-phone" style={{ transform: `scale(${s})` }}>
        <i className="pf-key pf-k1" aria-hidden /><i className="pf-key pf-k2" aria-hidden /><i className="pf-key pf-k3" aria-hidden /><i className="pf-key pf-k4" aria-hidden />
        <div className="pf-screen">
          {fallback && <div className="pf-fallback">{fallback}</div>}
          {src && <LiveApp key={src} src={src} title={title} />}
          <div className="pf-status" aria-hidden><span className="pf-time">{time}</span><StatusIcons /></div>
          <i className="pf-island" aria-hidden />
          <i className="pf-home" aria-hidden />
        </div>
      </div>
    </div>
  );
}

function LiveApp({ src, title }: { src: string; title: string }) {
  const box = useRef<HTMLDivElement>(null);
  const [seen, setSeen] = useState(false);
  const [ready, setReady] = useState(false);
  // 화면에 들어올 때 붙인다: 화면 밖 다른 출처 iframe은 브라우저가 그리기를 미뤄 빈 상자로 남는다.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    const io = new IntersectionObserver((es) => es.some((e) => e.isIntersecting) && setSeen(true), { rootMargin: '0px' });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return (
    <div ref={box} className={`pf-live${ready ? ' ready' : ''}`}>
      {seen && (
        <iframe
          className="pf-app"
          src={src}
          title={title}
          allow="microphone; autoplay"
          onLoad={() => window.setTimeout(() => setReady(true), 700)}
        />
      )}
    </div>
  );
}
