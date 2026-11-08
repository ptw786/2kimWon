import {Heart,Volume2} from 'lucide-react'
import CallControls from './CallControls'
export default function IncomingCall({resident,busy,ringtone,onAccept,onDecline}){
 return <section className="phone-card incoming-card" aria-label="전화 수신"><div className="phone-top"><span>안심온</span><span>전화 수신</span></div><div className="phone-middle"><div className="avatar"><Heart fill="currentColor" size={56}/></div><p className="phone-caption">안심온에서 전화가 왔습니다</p><h1 className="phone-heading">안심온 돌봄전화</h1><p className="phone-subtitle">{resident.name} 님, 오늘도 안녕하세요</p></div>
 <div className="ringtone-status" role="status">{ringtone.status==='ringing'?'전화가 울리고 있어요':ringtone.status==='unavailable'?'이 브라우저에서는 벨소리를 사용할 수 없어요. 아래 버튼으로 전화를 받아 주세요.':'소리 없이 전화가 표시되고 있어요'}</div>
 {['idle','blocked'].includes(ringtone.status)&&<button className="ringtone-enable" onClick={ringtone.start} disabled={busy}><Volume2/>벨소리 켜기</button>}
 <CallControls incoming busy={busy} onAccept={onAccept} onDecline={onDecline}/></section>
}
