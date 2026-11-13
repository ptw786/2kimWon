// 시각은 모두 한국 시간으로 보여 준다.
const TZ = 'Asia/Seoul';

const fmt = (opts: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat('ko-KR', { timeZone: TZ, ...opts });
const dateLong = fmt({ month: 'long', day: 'numeric', weekday: 'long' });
const time12 = fmt({ hour: 'numeric', minute: '2-digit', hour12: true });
const hm = fmt({ hour: '2-digit', minute: '2-digit', hour12: false });
const hms = fmt({ hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
const md = fmt({ month: 'long', day: 'numeric' });
const ymd = fmt({ year: 'numeric', month: '2-digit', day: '2-digit' });

/** 11월 14일 금요일 · 오전 11:40 */
export const nowHeadline = (d = new Date()) => `${dateLong.format(d)} · ${time12.format(d)}`;
export const hhmm = (iso: string) => hm.format(new Date(iso));
export const hhmmss = (iso: string) => hms.format(new Date(iso));
export const monthDay = (iso: string) => md.format(new Date(iso));

/** YYYY-MM-DD (한국 시간) */
export function kstDate(d = new Date()): string {
  const p = Object.fromEntries(ymd.formatToParts(d).map((x) => [x.type, x.value]));
  return `${p.year}-${p.month}-${p.day}`;
}

/** '2026-11-14' → 14, 오늘이면 '오늘' */
export const dayLabel = (date: string) => (date === kstDate() ? '오늘' : String(Number(date.slice(8, 10))));

/** 3분 12초 */
export function duration(start: string | null, end: string | null): string | null {
  if (!start || !end) return null;
  const s = Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 1000));
  const m = Math.floor(s / 60);
  return m ? `${m}분 ${String(s % 60).padStart(2, '0')}초` : `${s}초`;
}

/** 412ms · 1.2s · — */
export const msLabel = (ms: number | null) => (ms == null ? '—' : ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`);
