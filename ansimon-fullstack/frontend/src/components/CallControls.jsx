import {Phone,PhoneOff} from 'lucide-react'
export default function CallControls({incoming=false,busy,onAccept,onDecline,onFinish,complete=false}){
 if(incoming)return <div className="phone-actions"><div><button className="callcircle reject" aria-label="수신 거절" disabled={busy} onClick={onDecline}><PhoneOff size={36}/></button><span>거절</span></div><div><button className="callcircle accept" aria-label="전화 받기" disabled={busy} onClick={onAccept}><Phone size={36}/></button><span>전화 받기</span></div></div>
 return <div className="phone-end"><button disabled={busy} className="callcircle reject" aria-label={complete?'완료 저장':'통화 종료'} onClick={onFinish}><PhoneOff size={36}/></button><span>{complete?'완료 저장':'통화 종료'}</span></div>
}
