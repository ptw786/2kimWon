import {useCallback,useEffect,useRef,useState} from 'react'
import {api,post} from '../api'

const initial={phase:'loading',resident:null,questions:[],callId:null,count:0,messages:[],question:'',answer:'',seconds:0,startedAt:null,sound:true,listening:false,busy:true,error:'',result:''}
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
 const current=useRef(initial),alive=useRef(false),busy=useRef(true),controller=useRef(null),recognition=useRef(null),keys=useRef(null)
 const patch=useCallback(values=>{
  if(!alive.current)return
  current.current={...current.current,...values};setState(current.current)
 },[])
 const stopMedia=useCallback(()=>{
  if(recognition.current){
   const rec=recognition.current;recognition.current=null
   rec.onresult=null;rec.onerror=null;rec.onend=null
   try{rec.abort()}catch{}
  }
  window.speechSynthesis?.cancel()
 },[])
 const say=useCallback(text=>{
  if(!alive.current||current.current.phase!=='active'||!current.current.sound||!window.speechSynthesis)return
  window.speechSynthesis.cancel()
  const speech=new SpeechSynthesisUtterance(text);speech.lang='ko-KR';speech.rate=.86
  window.speechSynthesis.speak(speech)
 },[])
 const restoreDetail=useCallback(detail=>{
  const count=detail.turns.length
  patch({callId:detail.id,count,startedAt:Date.parse(detail.started_at),
   phase:detail.status==='in_progress'?'active':'ended',result:results[detail.status]||'',
   question:current.current.questions[count]?.text||'',
   messages:[...detail.turns.flatMap(t=>[{who:'ai',text:t.question},{who:'user',text:t.answer}]),
    ...(detail.status==='in_progress'&&current.current.questions[count]?[{who:'ai',text:current.current.questions[count].text}]:[])]})
 },[patch])
 const load=useCallback(async()=>{
  controller.current?.abort();stopMedia()
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
    if(!request.signal.aborted)restoreDetail(detail)
   }else patch({phase:'incoming'})
  }catch(e){if(!request.signal.aborted)patch({phase:'error',error:e.message})}
  finally{if(!request.signal.aborted){busy.current=false;patch({busy:false})}}
 },[elderId,patch,restoreDetail,stopMedia])
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
  busy.current=true;patch({busy:true,error:'',listening:false});stopMedia()
  const request=controller.current
  try{await task(request.signal)}
  catch(e){if(!request.signal.aborted)patch({error:e.message})}
  finally{if(!request.signal.aborted){busy.current=false;patch({busy:false})}}
 }
 const begin=()=>{
  if(current.current.phase!=='incoming')return
  return transact(async signal=>{
   const call=await post(`/residents/${elderId}/calls`,{},keys.current.start,{signal})
   const detail=await api(`/calls/${call.id}`,{signal})
   if(signal.aborted)return
   restoreDetail(detail);say(current.current.question)
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
  if(!signal.aborted){patch({phase:'ended',result:results[result.status],count:result.answered,question:''});clearKeys();stopMedia()}
 }
 const finish=()=>{
  if(current.current.phase!=='active')return
  return transact(signal=>saveFinish(current.current.count===5?'completed':'interrupted',signal))
 }
 const submit=value=>{
  const answer=value.trim()
  if(!answer||current.current.phase!=='active'||current.current.count===5)return
  return transact(async signal=>{
   const result=await post(`/calls/${current.current.callId}/turns`,{answer,index:current.current.count},undefined,{signal})
   if(signal.aborted)return
   patch({answer:'',count:result.count,question:result.next_question||'',messages:[...current.current.messages,
    {who:'user',text:answer},{who:'ai',text:result.reply},...(result.next_question?[{who:'ai',text:result.next_question}]:[])]})
   if(result.finished)await saveFinish('completed',signal)
   else say(result.reply+' '+result.next_question)
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
 return {...state,begin,decline,finish,submit,microphone,reset,reload:load,
  setAnswer:answer=>patch({answer}),toggleSound:()=>{stopMedia();patch({sound:!current.current.sound,listening:false})}}
}
