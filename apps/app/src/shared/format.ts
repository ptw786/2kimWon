/** '10:00' → '오전 10시', '14:30' → '오후 2시 30분' */
export function koreanTime(hhmm: string | null | undefined): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(hhmm ?? '')
  if (!m) return hhmm ?? ''
  const h = Number(m[1]), min = Number(m[2])
  const half = h < 12 ? '오전' : '오후'
  const h12 = h % 12 === 0 ? 12 : h % 12
  return `${half} ${h12}시${min ? ` ${min}분` : ''}`
}

/** '10:31' → '오전 10:31' */
export function clockLabel(hhmm: string): string {
  const m = /^(\d{1,2}):(\d{2})/.exec(hhmm)
  if (!m) return hhmm
  const h = Number(m[1])
  return `${h < 12 ? '오전' : '오후'} ${h % 12 === 0 ? 12 : h % 12}:${m[2]}`
}

function kstToday(offset = 0): string {
  return new Date(Date.now() + 9 * 3600_000 + offset * 86400_000).toISOString().slice(0, 10)
}

/** 'YYYY-MM-DD' → '오늘' | '어제' | '11월 12일' (한국 시간 기준) */
export function dayLabel(date: string): string {
  if (date === kstToday(0)) return '오늘'
  if (date === kstToday(-1)) return '어제'
  const [, mo, d] = date.split('-').map(Number)
  return `${mo}월 ${d}일`
}

/** 시간대별 인사 (한국 시간) */
export function greeting(now = new Date()): string {
  const h = new Date(now.getTime() + 9 * 3600_000).getUTCHours()
  if (h >= 5 && h < 11) return '좋은 아침이에요'
  if (h >= 11 && h < 17) return '편안한 오후예요'
  if (h >= 17 && h < 21) return '편안한 저녁이에요'
  return '편안한 밤 되세요'
}
