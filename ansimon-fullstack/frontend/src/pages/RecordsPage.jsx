import {useCallback,useEffect,useRef,useState} from 'react'
import {RefreshCw,X} from 'lucide-react'
import {api} from '../api'
import {Pill,formatDate,classificationLabel} from '../components/Common'
import {ErrorNotice,Loading} from '../components/Feedback'
import {useResource} from '../hooks/useResource'
const loadCalls=signal=>api('/calls',{signal})
export default function RecordsPage(){
 const {data:calls=[],loading,error,reload}=useResource(loadCalls)
 const [selected,setSelected]=useState(null),[detail,setDetail]=useState(null),[detailError,setDetailError]=useState(''),[detailLoading,setDetailLoading]=useState(false),[attempt,setAttempt]=useState(0)
 const closeButton=useRef(null),lastFocus=useRef(null)
 const close=useCallback(()=>{setSelected(null);setDetail(null);lastFocus.current?.focus()},[])
 useEffect(()=>{
  if(selected===null)return
  const controller=new AbortController()
  setDetail(null);setDetailError('');setDetailLoading(true)
  api(`/calls/${selected}`,{signal:controller.signal}).then(result=>{if(!controller.signal.aborted)setDetail(result)}).catch(e=>{if(!controller.signal.aborted)setDetailError(e.message)}).finally(()=>{if(!controller.signal.aborted)setDetailLoading(false)})
  closeButton.current?.focus()
  return()=>controller.abort()
 },[selected,attempt])
 useEffect(()=>{
  if(selected===null)return
  const keydown=e=>{
   if(e.key==='Escape')close()
   // Keep keyboard navigation inside the dialog (close and optional retry).
   if(e.key==='Tab'){
    const buttons=[...closeButton.current.closest('[role="dialog"]').querySelectorAll('button:not(:disabled)')]
    const first=buttons[0],last=buttons.at(-1)
    if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}
    else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}
   }
  }
  document.addEventListener('keydown',keydown)
  return()=>document.removeEventListener('keydown',keydown)
 },[selected,close])
 return <><ErrorNotice error={error} retry={reload} busy={loading}/><Loading loading={loading}/>
 <div className="page-title"><div><span className="eyebrow">CALL HISTORY</span><h1>통화 기록</h1><p>저장된 안부 확인 결과와 대화 내용을 확인하세요.</p></div><button className="outline" onClick={reload} disabled={loading}><RefreshCw size={16}/> 새로고침</button></div>
 <section className="panel"><div className="section-top"><h2>전체 기록 <span className="muted">({calls?.length||0})</span></h2></div><div className="tablewrap"><table><thead><tr><th>어르신</th><th>통화 날짜</th><th>결과</th><th>대화 요약</th><th>상세</th></tr></thead><tbody>{calls?.map(c=><tr key={c.id}><td><b>{c.resident_name}</b></td><td className="nowrap">{formatDate(c.started_at)}</td><td><Pill status={c.status}/></td><td className="summary-cell">{c.summary||'통화 중'}</td><td><button className="table-btn" onClick={e=>{lastFocus.current=e.currentTarget;setSelected(c.id)}}>보기</button></td></tr>)}</tbody></table>{!loading&&!error&&calls?.length===0&&<div className="empty">아직 저장된 통화 기록이 없습니다. 안부전화를 먼저 체험해 보세요.</div>}</div></section>
 {selected!==null&&<div className="modal-bg" onClick={close}><div className="modal" role="dialog" aria-modal="true" aria-label="통화 상세" onClick={e=>e.stopPropagation()}><div className="section-top"><h2>통화 상세 #{selected}</h2><button ref={closeButton} className="iconbutton" aria-label="닫기" onClick={close}><X/></button></div><Loading loading={detailLoading}/><ErrorNotice error={detailError} retry={()=>setAttempt(n=>n+1)} busy={detailLoading}/>{detail&&<><Pill status={detail.status}/><p>{formatDate(detail.started_at)}</p><p className="modal-summary">{detail.summary||'요약 없음'}</p><div className="detail-turns">{(detail.attempts?.length?detail.attempts:detail.turns).map(t=><div key={t.id}><small>안심온 질문</small><p>{t.question}</p><small>어르신 답변</small><p className="reply">{t.answer}</p><small>{classificationLabel(t.classification)}{t.attempt>0?` · 재답변 ${t.attempt}/2`:""}</small>{t.reply&&<p>{t.reply}</p>}{Boolean(t.emergency)&&<p>직접 119 연락 안내 제공 · 자동 신고 없음</p>}</div>)}</div></>}</div></div>}</>
}
