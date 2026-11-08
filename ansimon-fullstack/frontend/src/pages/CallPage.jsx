import {Link} from 'react-router-dom'
import {CheckCircle2,RefreshCw} from 'lucide-react'
import {Brand} from '../components/Common'
import {ErrorNotice,Loading} from '../components/Feedback'
import IncomingCall from '../components/IncomingCall'
import ActiveCall from '../components/ActiveCall'
import ConversationPanel from '../components/ConversationPanel'
import {useCall} from '../hooks/useCall'
import {useRingtone} from '../hooks/useRingtone'
export default function CallPage({elderId}){
 const call=useCall(elderId)
 const ringtone=useRingtone(call.phase==='incoming'&&!call.busy)
 const accept=()=>{ringtone.stop();call.begin()}
 const decline=()=>{ringtone.stop();call.decline()}
 return <div className="elder-call"><header className="call-header"><Brand/><nav aria-label="전화 화면 메뉴"><Link to="/">관리 화면</Link><Link to="/records">통화 기록</Link></nav></header>
 <main className="call-content"><Loading loading={call.phase==='loading'}/><ErrorNotice error={call.error} retry={call.pendingAnswer?call.retryAnswer:call.phase==='active'&&call.count===5?call.finish:call.phase==='error'||call.phase==='incoming'?call.reload:undefined} busy={call.busy}/>
 {call.emergency&&<div className="emergency-notice" role="alert">긴급한 도움이 필요할 수 있습니다. 지금 직접 119에 연락하거나 가까운 분에게 도움을 요청해 주세요. 안심온은 실제 119 신고를 하지 않습니다.</div>}
 {call.ttsNotice&&<p className="tts-notice" role="status">{call.ttsNotice}</p>}
 {call.phase==='invalid'&&<section className="route-message"><h1>어르신 정보를 확인해 주세요</h1><Link to="/">어르신 목록으로 이동</Link></section>}
 {call.phase==='incoming'&&<IncomingCall resident={call.resident} busy={call.busy} ringtone={ringtone} onAccept={accept} onDecline={decline}/>}
 {call.phase==='active'&&<div className="elder-active-layout"><ActiveCall {...call} onSound={call.toggleSound} onMicrophone={call.microphone} onFinish={()=>{ringtone.stop();call.finish()}}/><ConversationPanel {...call} disabled={call.busy||call.speaking||call.pendingAnswer||call.count===5} onSubmit={call.submit}/></div>}
 {call.phase==='ended'&&<section className="phone-card ended-card"><div className="phone-ended"><CheckCircle2 size={64}/><h1>통화가 종료되었습니다</h1><p>{call.result}</p><p>{call.resident.name} 님, 편안한 하루 보내세요.</p><button onClick={call.reset}><RefreshCw/>다시 전화받기</button><Link to="/records">통화 기록 확인</Link><Link to="/">관리 화면으로 이동</Link></div></section>}
 <p className="call-disclaimer">웹 안부전화 체험입니다. 실제 전화망에 연결되지 않습니다.</p>
 </main></div>
}
