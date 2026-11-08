import {useCallback,useEffect,useRef,useState} from 'react'
import {api,post} from '../api'

const initial={phase:'loading',resident:null,questions:[],callId:null,count:0,attempt:0,retryCount:0,pendingAnswer:false,speaking:false,speakingText:'',ttsNotice:'',emergency:false,messages:[],question:'',answer:'',seconds:0,startedAt:null,sound:true,listening:false,busy:true,error:'',result:''}
const results={completed:'안부 확인 완료',interrupted:'통화 중단',declined:'수신 거절'}
const validId=id=>/^[1-9]\d*$/.test(id)&&Number.isSafeInteger(Number(id))
function requestKeys(id){
 const storageKey=`ansimon:incoming:${id}`
 try{
  const saved=JSON.parse(sessionStorage.getItem(storageKey)||'null')
  if(saved?.start&&saved?.decline)return saved
 }catch{}
 const keys={start:crypto.randomUUID(),decline:crypto.randomUUID()}
 try{sessionStorage.setItem(storageKey,JSON.stringify(keys))}catch{}
 return keys
}
export function useCall(elderId){
 const [state,setState]=useState(initial)
 const current=useRef(initial),alive=useRef(false),busy=useRef(true),controller=useRef(null),recognition=useRef(null),keys=useRef(null),speechTask=useRef(null),pending=useRef(null),operation=useRef(0)
 const patch=useCallback(values=>{
  if(!alive.current)return
  current.current={...current.current,...values};setState(current.current)
 },[])
 const stopSpeech=useCallback((continueSequence=false)=>{
  speechTask.current?.settle(continueSequence)
  window.speechSynthesis?.cancel()
 },[])
 const stopMedia=useCallback((continueSequence=false)=>{
  if(recognition.current){
   const rec=recognition.current;recognition.current=null
   rec.onresult=null;rec.onerror=null;rec.onend=null
   try{rec.abort()}catch{}
  }
  stopSpeech(continueSequence)
 },[stopSpeech])
 const say=useCallback(text=>{
  if(!alive.current||current.current.phase!=='active')return Promise.resolve(false)
  if(!text||!current.current.sound)return Promise.resolve(true)
  if(!window.speechSynthesis){patch({ttsNotice:'음성 출력을 지원하지 않아 화면의 글로 안내합니다.'});return Promise.resolve(true)}
  stopSpeech()
  return new Promise(resolve=>{
   const speech=new SpeechSynthesisUtterance(text)
   const task={settle:null,timer:null}
   task.settle=proceed=>{
    if(speechTask.current!==task)return
    clearTimeout(task.timer);speech.onend=null;speech.onerror=null
    speechTask.current=null;patch({speaking:false,speakingText:''});resolve(proceed)
   }
   speechTask.current=task
   speech.lang='ko-KR';speech.rate=.86
   speech.onend=()=>task.settle(true)
   speech.onerror=()=>{patch({ttsNotice:'음성을 재생하지 못해 화면의 글로 안내합니다.'});task.settle(true)}
   // Some browsers never deliver a speech end event when a voice is unavailable.
   task.timer=setTimeout(()=>{patch({ttsNotice:'음성 응답이 지연되어 화면의 글로 안내합니다.'});task.settle(true);window.speechSynthesis.cancel()},Math.min(60000,Math.max(8000,text.length*450)))
   patch({speaking:true,speakingText:text})
   try{window.speechSynthesis.speak(speech)}catch{speech.onerror?.()}
  })
 },[patch,stopSpeech])
 const restoreDetail=useCallback(detail=>{
  const dialogue=detail.dialogue_state||{count:detail.turns.length,attempt:0,retry_count:0,question:current.current.questions[detail.turns.length]?.text||''}
  const messages=[]
  for(let index=0;index<5;index++){
   const attempts=detail.attempts?.filter(item=>item.question_index===index)||[]
   if(attempts.length){
    for(const item of attempts)messages.push({who:'ai',text:item.question},{who:'user',text:item.answer,classification:item.classification},{who:'ai',text:item.reply})
   }else if(detail.turns[index]){
    const turn=detail.turns[index]
    messages.push({who:'ai',text:turn.question},{who:'user',text:turn.answer,classification:turn.classification})
    if(turn.reply)messages.push({who:'ai',text:turn.reply})
   }
  }
  if(detail.status==='in_progress'&&dialogue.question)messages.push({who:'ai',text:dialogue.question})
  patch({callId:detail.id,count:dialogue.count,attempt:dialogue.attempt,retryCount:dialogue.retry_count,
   startedAt:Date.parse(detail.started_at),phase:detail.status==='in_progress'?'active':'ended',
   result:results[detail.status]||'',question:dialogue.question||'',messages,
   emergency:[...detail.turns,...(detail.attempts||[])].some(item=>item.emergency)})
 },[patch])
 const load=useCallback(async()=>{
  const id=++operation.current
  controller.current?.abort();stopMedia();pending.current=null
  const request=new AbortController();controller.current=request
  busy.current=true;patch({...initial,sound:current.current.sound})
  if(!validId(elderId)){
   patch({phase:'invalid',error:'어르신 주소가 올바르지 않습니다.',busy:false});busy.current=false;return
  }
  keys.current=requestKeys(elderId)
  try{
   const [residents,questions,calls]=await Promise.all([
    api('/residents',{signal:request.signal}),api('/questions',{signal:request.signal}),api(`/calls?resident_id=${elderId}&limit=500`,{signal:request.signal})])
   if(request.signal.aborted)return
   const resident=residents.find(r=>r.id===Number(elderId))
   if(!resident){patch({phase:'invalid',error:'해당 어르신을 찾을 수 없습니다.'});return}
   patch({resident,questions,question:questions[0]?.text||''})
   const ongoing=calls.find(call=>call.status==='in_progress')
   if(ongoing){
    const detail=await api(`/calls/${ongoing.id}`,{signal:request.signal})
    if(!request.signal.aborted){restoreDetail(detail);await say(current.current.question)}
   }else patch({phase:'incoming'})
  }catch(e){if(!request.signal.aborted)patch({phase:'error',error:e.message})}
  finally{if(!request.signal.aborted&&operation.current===id){busy.current=false;patch({busy:false})}}
 },[elderId,patch,restoreDetail,say,stopMedia])
 useEffect(()=>{
  alive.current=true;load()
  return()=>{alive.current=false;controller.current?.abort();stopMedia()}
 },[load,stopMedia])
 useEffect(()=>{
  if(state.phase!=='active')return
  const tick=()=>patch({seconds:Math.max(0,Math.floor((Date.now()-(current.current.startedAt||Date.now()))/1000))})
  tick();const interval=setInterval(tick,1000);return()=>clearInterval(interval)
 },[state.phase,patch])
 const clearKeys=()=>{try{sessionStorage.removeItem(`ansimon:incoming:${elderId}`)}catch{}}
 const transact=async task=>{
  if(busy.current||!alive.current)return
  const id=++operation.current
  busy.current=true;patch({busy:true,error:'',listening:false});stopMedia()
  const request=controller.current
  try{await task(request.signal)}
  catch(e){if(!request.signal.aborted&&operation.current===id)patch({error:e.message})}
  finally{if(!request.signal.aborted&&operation.current===id){busy.current=false;patch({busy:false})}}
 }
 const begin=()=>{
  if(current.current.phase!=='incoming')return
  return transact(async signal=>{
   const call=await post(`/residents/${elderId}/calls`,{},keys.current.start,{signal})
   const detail=await api(`/calls/${call.id}`,{signal})
   if(signal.aborted)return
   restoreDetail(detail);await say(current.current.question)
  })
 }
 const decline=()=>{
  if(current.current.phase!=='incoming')return
  return transact(async signal=>{
   await post(`/residents/${elderId}/decline`,{},keys.current.decline,{signal})
   if(!signal.aborted){patch({phase:'ended',result:results.declined});clearKeys()}
  })
 }
 const saveFinish=async(status,signal)=>{
  const result=await post(`/calls/${current.current.callId}/finish`,{status},undefined,{signal})
  if(!signal.aborted){patch({phase:'ended',result:results[result.status],count:result.answered,question:'',pendingAnswer:false});pending.current=null;clearKeys();stopMedia()}
 }
 const finish=()=>{
  if(current.current.phase!=='active')return
  // Ending is available while TTS is speaking; invalidate its pending sequence.
  if(current.current.speaking){operation.current++;stopMedia();busy.current=false}
  return transact(signal=>saveFinish(current.current.count===5?'completed':'interrupted',signal))
 }
 const submit=value=>{
  const answer=value.trim()
  if(busy.current||!answer||current.current.phase!=='active'||current.current.count===5)return
  const body=pending.current||{answer,index:current.current.count,attempt:current.current.attempt}
  pending.current=body
  patch({answer:body.answer,pendingAnswer:true})
  return transact(async signal=>{
   const result=await post(`/calls/${current.current.callId}/turns`,body,undefined,{signal})
   if(signal.aborted)return
   pending.current=null
   patch({answer:'',pendingAnswer:false,count:result.count,attempt:result.next_attempt,
    retryCount:result.needs_retry?result.retry_count:0,
    emergency:current.current.emergency||result.emergency,
    messages:[...current.current.messages,{who:'user',text:body.answer,classification:result.classification},{who:'ai',text:result.reply}]})
   // Speak the follow-up first. Only its completion displays/speaks the next prompt.
   if(!await say(result.reply)||signal.aborted)return
   if(result.finished){
    const closing='안부 확인을 마쳤습니다. 오늘도 편안한 하루 보내세요.'
    patch({question:'',messages:[...current.current.messages,{who:'ai',text:closing}]})
    if(await say(closing)&&!signal.aborted)await saveFinish('completed',signal)
   }else{
    patch({question:result.next_question,messages:[...current.current.messages,{who:'ai',text:result.next_question}]})
    await say(result.next_question)
   }
  })
 }
 const microphone=()=>{
  if(current.current.listening){recognition.current?.stop();return}
  if(busy.current||current.current.phase!=='active'||current.current.count===5)return
  const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition
  if(!Recognition){patch({error:'이 브라우저는 음성 인식을 지원하지 않습니다. 텍스트로 답변해 주세요.'});return}
  stopMedia()
  const rec=new Recognition();recognition.current=rec;rec.lang='ko-KR';rec.interimResults=false
  rec.onresult=e=>{
   if(!alive.current||recognition.current!==rec)return
   const text=e.results?.[0]?.[0]?.transcript
   patch({listening:false});if(text)submit(text)
  }
  rec.onerror=e=>{if(alive.current&&recognition.current===rec){patch({listening:false,...(e.error!=='aborted'?{error:'마이크 인식 오류: '+e.error+' · 텍스트 입력을 사용해 주세요.'}:{})})}}
  rec.onend=()=>{if(alive.current&&recognition.current===rec){recognition.current=null;patch({listening:false})}}
  try{rec.start();patch({listening:true})}catch{recognition.current=null;patch({error:'마이크를 실행할 수 없습니다. 브라우저 권한을 확인하세요.'})}
 }
 const reset=()=>{if(busy.current)return;clearKeys();load()}
 return {...state,begin,decline,finish,submit,microphone,reset,reload:load,retryAnswer:()=>submit(pending.current?.answer||current.current.answer),
  setAnswer:answer=>patch({answer}),toggleSound:()=>{patch({sound:!current.current.sound,listening:false});stopMedia(true)}}
}
