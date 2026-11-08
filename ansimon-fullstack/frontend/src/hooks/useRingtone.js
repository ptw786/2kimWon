import {useCallback,useEffect,useRef,useState} from 'react'

// One context, two quiet oscillators and one cadence timer per incoming screen.
export function useRingtone(enabled){
 const session=useRef(null),alive=useRef(false)
 const [status,setStatus]=useState('idle')
 const dispose=useCallback(()=>{
  const current=session.current
  session.current=null
  if(!current)return
  clearInterval(current.timer)
  current.context.onstatechange=null
  if(current.gain){current.gain.gain.cancelScheduledValues(0);current.gain.gain.value=0}
  for(const node of current.oscillators){try{node.stop()}catch{}node.disconnect()}
  current.gain?.disconnect()
  if(current.context.state!=='closed')current.context.close().catch(()=>{})
 },[])
 const stop=useCallback(()=>{dispose();if(alive.current)setStatus('idle')},[dispose])
 const start=useCallback(()=>{
  if(!alive.current||!enabled)return
  const AudioContext=window.AudioContext||window.webkitAudioContext
  if(!AudioContext){setStatus('unavailable');return}
  let current=session.current
  try{
   if(!current){
    const context=new AudioContext()
    current={context,gain:null,oscillators:[],timer:null}
    session.current=current
    const gain=context.createGain();current.gain=gain
    gain.gain.value=0;gain.connect(context.destination)
    for(const frequency of [440,480]){
     const oscillator=context.createOscillator();current.oscillators.push(oscillator)
     oscillator.type='sine';oscillator.frequency.value=frequency
     oscillator.connect(gain);oscillator.start()
    }
   }
   const update=()=>{
    if(!alive.current||session.current!==current)return
    if(current.context.state!=='running'){
     clearInterval(current.timer);current.timer=null
     setStatus('blocked');return
    }
    if(!current.timer){
     const pulse=()=>{
      const time=current.context.currentTime,gain=current.gain.gain
      gain.cancelScheduledValues(time);gain.setValueAtTime(0,time)
      for(const offset of [0,1.2]){
       gain.setValueAtTime(0,time+offset)
       gain.linearRampToValueAtTime(.045,time+offset+.025)
       gain.setValueAtTime(.045,time+offset+.75)
       gain.linearRampToValueAtTime(0,time+offset+.8)
      }
     }
     pulse();current.timer=setInterval(pulse,4000)
    }
    setStatus('ringing')
   }
   current.context.onstatechange=update
   // Do not await resume: autoplay policy may leave its promise pending forever.
   if(current.context.state!=='running')current.context.resume().then(update).catch(()=>{
    if(alive.current&&session.current===current)setStatus('blocked')
   })
   update()
  }catch{dispose();if(alive.current)setStatus('unavailable')}
 },[enabled,dispose])
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;dispose()}},[dispose])
 useEffect(()=>{
  if(enabled)start()
  else stop()
  return dispose
 },[enabled,start,stop,dispose])
 return {status,start,stop}
}
