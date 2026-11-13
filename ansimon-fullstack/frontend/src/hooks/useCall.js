import {useCallback,useEffect,useRef,useState} from 'react'
import {api,post} from '../api'
import {browserStorage,saveDraft,clearDraft,resolveDraft,discardRecovered} from '../drafts'
import {SpeechInput} from '../speech/recognition'
import {SpeechOutput} from '../speech/synthesis'

const initial={phase:'loading',resident:null,questions:[],callId:null,count:0,attempt:0,retryCount:0,pendingAnswer:false,recoveredDraft:null,draftNotice:'',submitting:false,sttStatus:'idle',sttSupported:null,sttError:'',sttNotice:'',lastTranscript:'',interimTranscript:'',speaking:false,speakingText:'',ttsNotice:'',emergency:false,messages:[],question:'',answer:'',seconds:0,startedAt:null,sound:true,listening:false,busy:true,error:'',result:''}
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
 const current=useRef(initial),alive=useRef(false),busy=useRef(true),controller=useRef(null),speechInput=useRef(null),speechOutput=useRef(null),submitRef=useRef(null),keys=useRef(null),pending=useRef(null),operation=useRef(0)
 const patch=useCallback(values=>{
  if(!alive.current)return
  current.current={...current.current,...values};setState(current.current)
 },[])
 const stopSpeech=useCallback((continueSequence=false)=>speechOutput.current?.stop(continueSequence),[])
 const stopMedia=useCallback((continueSequence=false)=>{
  speechInput.current?.stop()
  stopSpeech(continueSequence)
 },[stopSpeech])
 const say=useCallback((text,key)=>{
  if(!alive.current||current.current.phase!=='active')return Promise.resolve(false)
  return speechOutput.current.speak(text,key)
 },[])
 const questionKey=()=>`${current.current.callId}:question:${current.current.count}:${current.current.attempt}`
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
  const draft=resolveDraft(browserStorage(),detail)
  pending.current=draft.pending
  patch({error:draft.pending?'이전에 저장 여부를 확인하지 못한 답변이 있습니다. 다시 시도해 주세요.':'',answer:draft.answer,pendingAnswer:Boolean(draft.pending),recoveredDraft:draft.recoveredDraft,callId:detail.id,count:dialogue.count,attempt:dialogue.attempt,retryCount:dialogue.retry_count,
   startedAt:Date.parse(detail.started_at),phase:detail.status==='in_progress'?'active':'ended',
   result:results[detail.status]||'',question:dialogue.safety_paused?'안전을 위해 질문을 멈췄습니다. 직접 119 또는 가까운 분에게 도움을 요청해 주세요.':dialogue.question||'',messages,
   emergency:[...detail.turns,...(detail.attempts||[])].some(item=>item.emergency)})
 },[patch])
 const load=useCallback(async()=>{
  const id=++operation.current
  controller.current?.abort();stopMedia();pending.current=null
  const request=new AbortController();controller.current=request
  busy.current=true;patch({...initial,sound:current.current.sound,sttSupported:speechInput.current?.supported||false})
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
    if(!request.signal.aborted){restoreDetail(detail);await say(current.current.question,questionKey())}
   }else patch({phase:'incoming'})
  }catch(e){if(!request.signal.aborted)patch({phase:'error',error:e.message})}
  finally{if(!request.signal.aborted&&operation.current===id){busy.current=false;patch({busy:false,submitting:false})}}
 },[elderId,patch,restoreDetail,say,stopMedia])
 useEffect(()=>{
  alive.current=true
  speechInput.current=new SpeechInput({host:window,
   canStart:()=>alive.current&&current.current.phase==='active'&&!busy.current&&!current.current.pendingAnswer&&!current.current.speaking&&current.current.count<5,
   onState:values=>{patch(values);const s=current.current;if(values.sttError&&s.phase==='active'&&s.count<5)post(`/calls/${s.callId}/input-events`,{source:'stt_error',message:values.sttError,index:s.count,attempt:s.attempt},undefined,{signal:controller.current?.signal}).catch(()=>{})},onFinal:text=>submitRef.current?.(text,'stt')})
  speechOutput.current=new SpeechOutput({host:window,beforeSpeak:()=>speechInput.current?.stop(),
   onState:patch,onNotice:ttsNotice=>patch({ttsNotice}),enabled:()=>current.current.sound})
  load()
  return()=>{alive.current=false;controller.current?.abort();speechInput.current?.dispose();speechOutput.current?.dispose()}
 },[load,patch])
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
  finally{if(!request.signal.aborted&&operation.current===id){busy.current=false;patch({busy:false,submitting:false})}}
 }
 const begin=()=>{
  if(current.current.phase!=='incoming')return
  return transact(async signal=>{
   const call=await post(`/residents/${elderId}/calls`,{},keys.current.start,{signal})
   const detail=await api(`/calls/${call.id}`,{signal})
   if(signal.aborted)return
   restoreDetail(detail);await say(current.current.question,questionKey())
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
  if(!signal.aborted){clearDraft(browserStorage(),current.current.callId,true);patch({recoveredDraft:null,phase:'ended',result:results[result.status],count:result.answered,question:'',pendingAnswer:false});pending.current=null;clearKeys();stopMedia()}
 }
 const finish=()=>{
  if(current.current.phase!=='active')return
  // Ending is available while TTS is speaking; invalidate its pending sequence.
  if(current.current.speaking){operation.current++;stopMedia();busy.current=false}
  return transact(signal=>saveFinish(current.current.count===5?'completed':'interrupted',signal))
 }
 const persistDraft=(answer,pending=false,source='text')=>{
  const s=current.current
  const ok=saveDraft(browserStorage(),s.callId,{answer,index:s.count,attempt:s.attempt,question:s.question,pending,source})
  patch({draftNotice:ok?'':'임시 저장을 사용할 수 없습니다. 새로고침하면 작성 중인 답변이 사라질 수 있습니다.'})
 }
 const submitAnswer=(value,source='text')=>{
  const answer=typeof value==='string'?value.trim():''
  if(busy.current||current.current.phase!=='active'||current.current.count===5)return
  if(!answer)return
  if(answer.length>500){patch({answer,error:'답변은 500자 이내로 입력해 주세요.'});return}
  const body=pending.current||{answer,index:current.current.count,attempt:current.current.attempt,engine:'hybrid',source}
  pending.current=body
  persistDraft(body.answer,true,body.source)
  patch({answer:body.answer,pendingAnswer:true,submitting:true,sttError:''})
  return transact(async signal=>{
   let result
   try{result=await post(`/calls/${current.current.callId}/turns`,body,undefined,{signal})}
   catch(error){
    if(error.status!==409){
     if(/119|구급차|응급차|숨.{0,4}못|가슴.{0,6}심하/.test(body.answer)){const guidance='긴급한 상황이면 지금 직접 119에 연락하거나 가까운 분에게 도움을 요청해 주세요. 안심온은 실제 신고를 하지 않습니다.';patch({ttsNotice:guidance});await say(guidance,`${current.current.callId}:safety-fallback:${body.index}:${body.attempt}`)}
     throw error
    }
    const detail=await api(`/calls/${current.current.callId}`,{signal})
    if(signal.aborted)return
    restoreDetail(detail)
    patch({error:'다른 화면에서 통화 상태가 변경되어 최신 상태를 불러왔습니다. 이전 질문의 미전송 답변은 따로 보관했으며 자동 전송하지 않습니다.'})
    if(detail.status==='active'||detail.status==='in_progress')await say(current.current.question,questionKey())
    return
   }
   if(signal.aborted)return
   pending.current=null
   clearDraft(browserStorage(),current.current.callId)
   patch({answer:'',pendingAnswer:false,submitting:false,count:result.count,attempt:result.next_attempt,
    retryCount:result.needs_retry?result.retry_count:0,
    emergency:current.current.emergency||result.emergency,
    messages:[...current.current.messages,{who:'user',text:body.answer,classification:result.classification},{who:'ai',text:result.reply}]})
   // Speak the follow-up first. Only its completion displays/speaks the next prompt.
   if(!await say(result.reply,`${current.current.callId}:reply:${body.index}:${body.attempt}`)||signal.aborted)return
   if(result.action==='safety_pause'){
    patch({question:'안전을 위해 질문을 멈췄습니다. 직접 119 또는 가까운 분에게 도움을 요청해 주세요.'});return
   }
   if(result.finished){
    const closing='안부 확인을 마쳤습니다. 오늘도 편안한 하루 보내세요.'
    patch({question:'',messages:[...current.current.messages,{who:'ai',text:closing}]})
    if(await say(closing,`${current.current.callId}:closing`)&&!signal.aborted)await saveFinish('completed',signal)
   }else{
    patch({question:result.next_question,messages:[...current.current.messages,{who:'ai',text:result.next_question}]})
    await say(result.next_question,questionKey())
   }
  })
 }
 submitRef.current=submitAnswer
 const microphone=()=>{
  if(speechInput.current?.active){speechInput.current.stop({manual:true});return}
  speechInput.current?.start()
 }
 const reset=()=>{if(busy.current)return;clearKeys();load()}
 return {...state,begin,decline,finish,submitAnswer,microphone,reset,reload:load,retryAnswer:()=>submitAnswer(pending.current?.answer||current.current.answer),
  setAnswer:answer=>{if(busy.current||current.current.pendingAnswer)return;speechInput.current?.stop();persistDraft(answer);patch({answer})},discardRecovered:()=>{discardRecovered(browserStorage(),current.current.callId);patch({recoveredDraft:null})},toggleSound:()=>{patch({sound:!current.current.sound,listening:false});stopMedia(true)}}
}
