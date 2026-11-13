import {useState} from 'react'
import PriorityAssessment from '../components/PriorityAssessment'
import {useNavigate} from 'react-router-dom'
import {ArrowRight,CalendarDays,CheckCircle2,Clock3,Headphones,PhoneOff,RefreshCw,Users} from 'lucide-react'
import {api} from '../api'
import {Pill} from '../components/Common'
import {ErrorNotice,Loading} from '../components/Feedback'
import {useResource} from '../hooks/useResource'

async function fetchDashboard(signal){
 const [d,r]=await Promise.allSettled([api('/dashboard',{signal}),api('/residents',{signal})])
 return {dashboard:d.status==='fulfilled'?d.value:null,
  residents:r.status==='fulfilled'?r.value.map(resident=>({...resident,...(d.status==='fulfilled'?d.value.residents.find(row=>row.id===resident.id):{})})):[],
  error:[d,r].filter(result=>result.status==='rejected').map(result=>result.reason.message).join(' / ')}
}
export default function DashboardPage(){
 const navigate=useNavigate()
 const [priority,setPriority]=useState(false)
 const {data,loading,error:requestError,reload:load}=useResource(fetchDashboard)
 const {dashboard=null,residents=[],error=''}=data||{}
 const displayResidents=priority?[...residents].sort((a,b)=>(b.assessment?.score??-1)-(a.assessment?.score??-1)):residents
 const choosePhone=id=>{if(id)navigate(`/call/${id}`)}
 return <><ErrorNotice error={requestError||error} retry={load} busy={loading}/><Loading loading={loading}/>
<><div className="page-title"><div><span className="eyebrow">DAILY CARE OVERVIEW</span><h1>오늘의 안부 확인</h1><p>어르신의 하루를 확인하고, 돌봄이 필요한 분들을 살펴보세요.</p></div><button className="outline" onClick={load}><RefreshCw size={16}/> 새로고침</button></div>
 <div className="stat-grid"><Stat icon={Users} label="관리 대상" value={dashboard?.total??'—'} unit="명"/><Stat icon={CheckCircle2} label="안부 확인 완료" value={dashboard?.completed??'—'} unit="명" accent/><Stat icon={Clock3} label="확인 대기" value={dashboard?.pending??'—'} unit="명"/><Stat icon={PhoneOff} label="미완료 · 중단" value={dashboard?dashboard.declined+dashboard.interrupted: '—'} unit="명"/></div>
 <section className="panel intro"><div className="intro-icon"><Headphones size={27}/></div><div><h2>전화 한 통으로 시작되는 안심</h2><p>안심온은 정해진 질문으로 일상을 확인합니다. 아직 전화하지 않은 어르신을 선택해 웹 안부전화를 체험해 보세요.</p></div><button className="bluebtn" disabled={!residents.length} onClick={()=>choosePhone(residents[0]?.id)}>체험하기 <ArrowRight size={16}/></button></section>
 <section className="panel"><div className="section-top"><div><h2>어르신 안부 현황</h2><p>가상 어르신 정보 · 오늘 마지막 통화 상태 기준</p></div><label><input type="checkbox" checked={priority} onChange={e=>setPriority(e.target.checked)}/> 확인 우선순위순</label><span className="date"><CalendarDays size={16}/>{dashboard?.date||'오늘'}</span></div><div className="tablewrap"><table><thead><tr><th>어르신</th><th>지역</th><th>예정 시각</th><th>오늘 상태</th><th>확인 우선순위</th><th>안부 확인</th></tr></thead><tbody>{displayResidents.map(r=><tr key={r.id}><td><div className="person"><span className="person-icon">{r.name[0]}</span><span><b>{r.name}</b><small>{r.age}세</small></span></div></td><td>{r.neighborhood}</td><td>{r.call_time}</td><td><Pill status={r.status}/></td><td><PriorityAssessment assessment={r.assessment}/></td><td><button className="table-btn" onClick={()=>choosePhone(r.id)}>전화 체험 <ArrowRight size={15}/></button></td></tr>)}</tbody></table></div></section></></>
}
function Stat({icon:Icon,label,value,unit,accent}){return <div className={'stat '+(accent?'accent':'')}><div className="stat-icon"><Icon size={20}/></div><div className="stat-label">{label}</div><div className="stat-num">{value}<span>{unit}</span></div></div>}
