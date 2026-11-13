import {useEffect,useRef,useState} from 'react'
import {Link} from 'react-router-dom'
import {api} from '../api'
import {useResource} from '../hooks/useResource'
import {ErrorNotice,Loading} from '../components/Feedback'
import {formatDate} from '../components/Common'
const fetchSchedules=async signal=>{
 const [schedules,residents]=await Promise.all([api('/schedules',{signal}),api('/residents',{signal})])
 return {...schedules,residents}
}
export default function SchedulesPage(){
 const {data,error,loading,reload}=useResource(fetchSchedules)
 const [editing,setEditing]=useState(null),[residentId,setResidentId]=useState(''),[recipient,setRecipient]=useState(''),[time,setTime]=useState('10:00')
 const [busy,setBusy]=useState(false),[writeError,setWriteError]=useState(''),[notice,setNotice]=useState('')
 const lock=useRef(false),mounted=useRef(false),controller=useRef(null)
 useEffect(()=>{mounted.current=true;const timer=setInterval(reload,10000);return()=>{mounted.current=false;clearInterval(timer);controller.current?.abort()}},[reload])
 const reset=()=>{setEditing(null);setRecipient('');setResidentId('');setTime('10:00')}
 const run=async action=>{
  if(lock.current)return
  lock.current=true;setBusy(true);setWriteError('');setNotice('')
  const request=new AbortController();controller.current=request
  try{await action(request.signal);if(!request.signal.aborted)await reload()}
  catch(e){if(mounted.current&&!request.signal.aborted)setWriteError(e.message)}
  finally{lock.current=false;if(mounted.current)setBusy(false)}
 }
 const save=e=>{e.preventDefault();run(async signal=>{
  await api(editing===null?'/schedules':`/schedules/${editing}`,{method:editing===null?'POST':'PUT',signal,body:JSON.stringify({resident_id:Number(residentId),call_time:time,...(recipient.trim()?{recipient:recipient.trim()}:{})})})
  if(!signal.aborted){reset();setNotice('매일 반복 예약을 저장했습니다.')}
 })}
 const edit=s=>{setEditing(s.id);setResidentId(s.resident_id?String(s.resident_id):'');setRecipient(s.recipient);setTime(s.call_time);setWriteError('')}
 return <><div className="page-title"><div><span className="eyebrow">DAILY CALL SCHEDULE</span><h1>안부전화 예약</h1><p>한국 시간 기준 매일 반복됩니다. 실제 전화 발신 대신 웹 수신 화면을 엽니다.</p></div><button className="outline" disabled={busy} onClick={reload}>새로고침</button></div>
 <ErrorNotice error={error} retry={reload} busy={loading}/><ErrorNotice error={writeError}/>{notice&&<p role="status">{notice}</p>}<Loading loading={loading&&!data}/>
 <section className="panel"><h2>{editing===null?'매일 안부전화 예약':'예약 수정'}</h2><form className="schedule-form" onSubmit={save}>
 <label>어르신<select aria-label="어르신" required value={residentId} disabled={busy} onChange={e=>setResidentId(e.target.value)}><option value="">대상 선택</option>{data?.residents.map(r=><option key={r.id} value={r.id}>{r.name} · {r.age}세</option>)}</select></label>
 <label>대상 별칭 (선택)<input aria-label="대상 별칭 (선택)" maxLength={30} value={recipient} disabled={busy} onChange={e=>setRecipient(e.target.value)} placeholder="비우면 어르신 이름 사용"/></label>
 <label>매일 통화 시간 (한국)<input aria-label="매일 통화 시간 (한국)" type="time" required value={time} disabled={busy} onChange={e=>setTime(e.target.value)}/></label>
 <button className="bluebtn" disabled={busy||!residentId} type="submit">{busy?'저장 중…':editing===null?'예약 추가':'예약 수정 저장'}</button>{editing!==null&&<button className="outline" disabled={busy} type="button" onClick={reset}>수정 취소</button>}</form></section>
 <section className="panel"><h2>예약 목록</h2><div className="tablewrap"><table><thead><tr><th>대상 별칭</th><th>시각</th><th>다음 회차</th><th>관리</th></tr></thead><tbody>{data?.schedules.map(s=><tr key={s.id}><td>{s.recipient}{!s.resident_id&&<p className="schedule-warning">이전 예약입니다. 수정에서 어르신을 연결하세요.</p>}</td><td>{s.call_time}</td><td>{formatDate(s.next_at)}</td><td><button className="table-btn" disabled={busy} onClick={()=>edit(s)}>수정</button> <button className="table-btn" disabled={busy} onClick={()=>{if(window.confirm('예약을 해제할까요? 기존 통화 기록은 보존됩니다.'))run(async signal=>{await api(`/schedules/${s.id}`,{method:'DELETE',signal});if(!signal.aborted){if(editing===s.id)reset();setNotice('예약을 해제했습니다.')}})}}>예약 해제</button></td></tr>)}</tbody></table></div>{data?.schedules.length===0&&<p>등록한 예약이 없습니다.</p>}</section>
 <section className="panel"><h2>대기 중인 예약 통화</h2><p>대기 목록은 10초마다 확인합니다. 서버를 다시 켜면 놓친 회차 중 최근 한 회차를 복구합니다.</p><ul className="scheduled-queue">{data?.pending.map(q=><li key={q.id}><div><b>{q.recipient}</b><p>{formatDate(q.scheduled_at)} · {q.state==='claimed'?'통화 중':'수신 대기'}</p></div>{q.resident_id?<Link className="bluebtn" to={`/call/${q.resident_id}?queue=${q.id}`}>{q.state==='claimed'?'통화 이어가기':'예약 통화 열기'}</Link>:<span>예약 수정에서 대상 연결 필요</span>}</li>)}</ul>{data?.pending.length===0&&<p>대기 중인 예약 통화가 없습니다.</p>}</section></>
}
