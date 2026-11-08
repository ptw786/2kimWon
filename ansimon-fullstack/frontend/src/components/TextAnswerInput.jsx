import {Send} from 'lucide-react'
export default function TextAnswerInput({answer,setAnswer,disabled,onSubmit}){
 return <><form className="reply-input" onSubmit={e=>{e.preventDefault();onSubmit(answer)}}><input aria-label="답변 입력" disabled={disabled} value={answer} onChange={e=>setAnswer(e.target.value)} placeholder="답변을 입력해 주세요" maxLength={500}/><button className="bluebtn" aria-label="답변 보내기" disabled={disabled||!answer.trim()} type="submit"><Send size={22}/><span>보내기</span></button></form><div className="answer-hints"><span>빠른 답변</span>{['오늘은 몸이 괜찮아요','아침 먹었어요','어제 잠을 잘 잤어요'].map(text=><button key={text} disabled={disabled} onClick={()=>onSubmit(text)}>{text}</button>)}</div></>
}
