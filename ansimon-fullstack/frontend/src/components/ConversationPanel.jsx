import {useEffect,useRef} from 'react'
import {classificationLabel} from './Common'
import TextAnswerInput from './TextAnswerInput'
export default function ConversationPanel({messages,count,answer,setAnswer,disabled,onSubmit}){
 const end=useRef(null)
 useEffect(()=>{end.current?.scrollIntoView({behavior:'smooth',block:'nearest'})},[messages])
 return <section className="panel conversation-panel" aria-label="통화 대화"><div className="section-top"><h2>안심온과 대화하기</h2><span className="step-indicator">{count} / 5</span></div><div className="progress"><span style={{width:`${count/5*100}%`}}/></div><div className="chatbox" role="log" aria-live="polite" aria-label="질문과 답변">{messages.map((message,index)=><div key={index} className={`chat ${message.who}`}><div className="chat-bubble"><small>{message.who==='ai'?'안심온':'내 답변'}</small><p>{message.text}</p>{message.classification&&<small className="answer-classification">{classificationLabel(message.classification)}</small>}</div></div>)}<div ref={end}/></div><TextAnswerInput answer={answer} setAnswer={setAnswer} disabled={disabled} onSubmit={onSubmit}/></section>
}
