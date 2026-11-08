import {Heart} from 'lucide-react'
const STATUS={pending:['대기','pending'],in_progress:['통화 중','progress'],completed:['완료','complete'],interrupted:['중단','stopped'],declined:['수신 거절','stopped']}
export function Pill({status}){const [label,kind]=STATUS[status]||['알 수 없음','pending'];return <span className={'pill '+kind}><span className="status-dot"/>{label}</span>}
export function Brand(){return <div className="brand"><div className="brandmark"><Heart fill="currentColor" size={19}/></div><span>안심<span className="brandblue">온</span></span><span className="brand-en">ANSIMON</span></div>}

export function formatDate(iso){return iso?new Date(iso).toLocaleString('ko-KR',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'}):'-'}

export const classificationLabel=value=>({positive:'긍정',negative:'부정',neutral:'중립',unknown:'확인 불가',unclassified:'기존 답변·미분류'}[value]||'분류 미확인')
