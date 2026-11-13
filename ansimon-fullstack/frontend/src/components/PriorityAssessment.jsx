const reasons={stt_error:'음성 인식 실패',interpretation:'답변 해석 불가',self_unknown:'본인 응답에 따른 미확인',degree:'정도 미확인',unanswered:'미응답 또는 질문 미진행'}
export default function PriorityAssessment({assessment:a,details=false}){
 if(!a)return <span>미확인</span>
 const legacy=a.version!=='review-v2'
 const number=(legacy||(!a.urgent&&a.grade!=='정보 부족'))&&a.score!==null&&a.score!==undefined
 return <div className="priority-assessment"><strong className={a.urgent?'priority-urgent':''}>{legacy?'이전 기준 · ':''}{a.grade}{number?` · ${a.score}점`:''}{!legacy&&!a.urgent&&a.score===null?' · 점수 산정 불가':''}{!legacy&&!a.urgent&&a.grade==='정보 부족'&&a.degree_missing?' · 불편함의 정도 확인 필요':''}</strong>
 <small style={{display:'block'}}>{legacy?'이전 기준 기록 · 최대 15점 기준과 별도':a.secondary}</small>
 {details&&<><p>시연용 확인 순서이며 의료적 판단이 아닙니다. 미확인 항목은 0점으로 계산하지 않습니다.</p><p>판정 기준: {a.version||'legacy-v1'}</p><ul>{a.items?.map(i=><li key={i.topic}>{i.label}: {i.score===null?reasons[i.reason]:`${i.score}점`}<p>원문 근거: {i.evidence||'없음'}</p></li>)}{legacy&&a.problems?.map((p,i)=><li key={i}>{p.topic} · {p.points}점 · {p.reason}</li>)}</ul>{a.safety_guidance_provided&&<p>직접 119 연락 안전 안내 제공 · 실제 신고 없음</p>}</>}
 </div>
}
