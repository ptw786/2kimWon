export default function PriorityAssessment({assessment,details=false}){
 if(!assessment)return <span>미확인</span>
 return <div className="priority-assessment"><strong className={assessment.urgent?'priority-urgent':''}>{assessment.grade}{assessment.score!==null&&assessment.score!==undefined?` · ${assessment.score}점`:''}</strong>{details&&<><p>시연용 확인 순서 지표이며 의료적 판단이 아닙니다.</p><ul>{assessment.problems?.map((p,i)=><li key={i}>{p.topic} · {p.points}점 · {p.reason}{p.evidence&&<p>발화 근거: {p.evidence}</p>}</li>)}{assessment.call_points>0&&<li>{assessment.call_reason} · {assessment.call_points}점</li>}{assessment.urgent&&<li>위험 표현 감지 · 직접 119 연락 안내 · 자동 신고 없음</li>}</ul></>}</div>
}
