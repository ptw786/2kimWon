// 뜻이 있는 선 아이콘(24×24, currentColor). 글자 기호(◇ ⌂ =)로는 뜻이 전해지지 않아 그림으로 바꿨다.
const PATHS = {
  body: 'M19.5 12.6 12 20l-7.5-7.4A4.6 4.6 0 0 1 12 6.3a4.6 4.6 0 0 1 7.5 6.3zM6.5 12.5h3l1.5-2.5 2 4 1.5-1.5h3',
  meal: 'M3.5 11h17a8.5 8.5 0 0 1-17 0zM9 3.5c-.9 1.2.9 2.2 0 3.5M13 3.5c-.9 1.2.9 2.2 0 3.5M8 21h8',
  sleep: 'M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5zM15 3.5h3l-3 3.5h3',
  med: 'M10.6 20.4a4.95 4.95 0 0 1-7-7l7-7a4.95 4.95 0 0 1 7 7zM7.1 9.9l7 7',
  mood: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM8.5 14.2s1.3 1.8 3.5 1.8 3.5-1.8 3.5-1.8M9 9.5h.01M15 9.5h.01',
  flask: 'M9 3h6M10 3v6.2L4.6 18.4A1.7 1.7 0 0 0 6.1 21h11.8a1.7 1.7 0 0 0 1.5-2.6L14 9.2V3M7.2 15h9.6',
  house: 'M3.5 10.5 12 4l8.5 6.5V20a1 1 0 0 1-1 1H15v-6H9v6H4.5a1 1 0 0 1-1-1z',
  scale: 'M12 3.5v17M7.5 20.5h9M4.5 7h15M4.5 7l-2.5 6a2.5 2.5 0 0 0 5 0zM19.5 7 17 13a2.5 2.5 0 0 0 5 0z',
  steth: 'M6 3.5v5a4 4 0 0 0 8 0v-5M10 12.5v2a5 5 0 0 0 10 0v-1.5M20 13a2 2 0 1 0 0-4 2 2 0 0 0 0 4z',
  userPlus: 'M9 11.5a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5zM2.5 20.5a6.5 6.5 0 0 1 13 0M19 8v6M16 11h6',
  lock: 'M6 11h12a1 1 0 0 1 1 1v8a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1v-8a1 1 0 0 1 1-1zM8 11V7.5a4 4 0 0 1 8 0V11M12 15v2.5',
  phone: 'M20.5 16.4v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 .6 3.7 2 2 0 0 1 2.6 1.5h3a2 2 0 0 1 2 1.7c.1 1 .4 1.9.7 2.8a2 2 0 0 1-.5 2.1L6.6 9.4a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.4c.9.3 1.8.6 2.8.7a2 2 0 0 1 1.7 2z',
  qr: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h2v2h-2zM18 14h2M14 18v2M18 18h2v2',
  arrowLeft: 'M19 12H5M11 6l-6 6 6 6',
  more: 'M5 12h.01M12 12h.01M19 12h.01',
  today: 'M4 5h16v15H4zM4 9.5h16M8.5 3v4M15.5 3v4M8 13.5h3M8 16.5h6',
  live: 'M12 13a1 1 0 1 0 0-2 1 1 0 0 0 0 2zM8.5 15.5a5 5 0 0 1 0-7M15.5 8.5a5 5 0 0 1 0 7M5.6 18.4a9 9 0 0 1 0-12.8M18.4 5.6a9 9 0 0 1 0 12.8',
  people: 'M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7zM2.5 20a6.5 6.5 0 0 1 13 0M16 4.3a3.5 3.5 0 0 1 0 6.4M18.5 14a6.5 6.5 0 0 1 3 6',
  list: 'M8 6h12M8 12h12M8 18h12M4 6h.01M4 12h.01M4 18h.01',
  rules: 'M12 3.5v17M7.5 20.5h9M4.5 7h15M4.5 7l-2.5 6a2.5 2.5 0 0 0 5 0zM19.5 7 17 13a2.5 2.5 0 0 0 5 0z',
  shield: 'M12 21s7.5-3.5 7.5-9.5V5.5L12 3 4.5 5.5v6C4.5 17.5 12 21 12 21zM8.8 12l2.2 2.2 4.2-4.4',
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({ name, size = 22, label }: { name: IconName; size?: number; label?: string }) {
  return (
    <svg className="ico-svg" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden={label ? undefined : true} role={label ? 'img' : undefined} aria-label={label}>
      <path d={PATHS[name]} />
    </svg>
  );
}
