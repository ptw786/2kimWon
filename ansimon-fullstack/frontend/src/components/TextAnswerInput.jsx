import {useRef} from 'react'
import {Send} from 'lucide-react'
export default function TextAnswerInput({answer,setAnswer,disabled,submitting=false,onSubmit}){
 const composing=useRef(false)
 const send=()=>{if(!disabled&&!submitting&&!composing.current&&answer.trim())onSubmit(answer)}
 return <><form className="reply-input" aria-label="텍스트 답변" aria-busy={submitting} onSubmit={e=>{e.preventDefault();send()}}>
 <input aria-label="답변 입력" disabled={disabled} value={answer} onChange={e=>setAnswer(e.target.value)} onCompositionStart={()=>{composing.current=true}} onCompositionEnd={()=>{composing.current=false}} onKeyDown={e=>{
  if(e.key!=='Enter')return
  e.preventDefault()
  if(!e.repeat&&!e.nativeEvent.isComposing&&e.nativeEvent.keyCode!==229)send()
 }} placeholder="답변을 입력해 주세요" maxLength={500}/>
 <button className="bluebtn" aria-label="답변 보내기" disabled={disabled||submitting||!answer.trim()} type="submit"><Send size={22}/><span>{submitting?'저장 중…':'보내기'}</span></button></form>
 {submitting&&<p className="submission-status" role="status">답변을 저장하고 있습니다.</p>}
 <div className="answer-hints"><span>빠른 답변</span>{['오늘은 몸이 괜찮아요','아침 먹었어요','어제 잠을 잘 잤어요'].map(text=><button key={text} disabled={disabled||submitting} onClick={()=>onSubmit(text)}>{text}</button>)}</div></>
}
