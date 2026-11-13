// Session-only drafts: survive refresh without retaining health text after this tab closes.
const key=id=>`ansimon:draft:${id}`
const recoveredKey=id=>`ansimon:recovered:${id}`
export function browserStorage(){try{return window.sessionStorage}catch{return null}}
export function saveDraft(storage,id,record){
 if(!storage||!id)return false
 try{storage.setItem(key(id),JSON.stringify(record));return true}catch{return false}
}
export function clearDraft(storage,id,all=false){try{storage?.removeItem(key(id));if(all)storage?.removeItem(recoveredKey(id))}catch{}}
export function resolveDraft(storage,detail){
 let saved,recovered
 try{saved=JSON.parse(storage?.getItem(key(detail.id))||'null');recovered=JSON.parse(storage?.getItem(recoveredKey(detail.id))||'null')}catch{}
 const state=detail.dialogue_state||{count:detail.turns.length,attempt:0}
 if(saved&&typeof saved.answer==='string'&&saved.answer.length<=500){
  const persisted=detail.attempts?.find(t=>t.question_index===saved.index&&t.attempt===saved.attempt)
  if(saved.pending&&persisted?.answer===saved.answer){clearDraft(storage,detail.id);saved=null}
  else if(detail.status==='in_progress'&&saved.index===state.count&&saved.attempt===state.attempt){
   return {answer:saved.answer,pending:saved.pending?{answer:saved.answer,index:saved.index,attempt:saved.attempt,engine:'hybrid',source:saved.source||'text'}:null,recoveredDraft:recovered}
  }else{
   // Never put an old question's answer into a new question's editable field.
   recovered=saved
   try{storage?.setItem(recoveredKey(detail.id),JSON.stringify(saved))}catch{}
   clearDraft(storage,detail.id)
  }
 }
 return {answer:'',pending:null,recoveredDraft:recovered}
}
export function discardRecovered(storage,id){try{storage?.removeItem(recoveredKey(id))}catch{}}
