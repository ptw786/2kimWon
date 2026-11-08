// Observe real Chromium audio nodes without replacing the Web Audio engine.
window.__audio=[]
window.__abortedRequests=0
window.__intervals=new Map()
const nativeInterval=window.setInterval,nativeClearInterval=window.clearInterval
window.setInterval=(callback,...args)=>{const id=nativeInterval(callback,...args);window.__intervals.set(id,callback.name);return id}
window.clearInterval=id=>{window.__intervals.delete(id);return nativeClearInterval(id)}
const nativeFetch=window.fetch
window.fetch=function(url,options={}){
 options.signal?.addEventListener('abort',()=>window.__abortedRequests++,{once:true})
 if(window.__holdQuestions&&String(url).endsWith('/api/questions')){
  return new Promise((_resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new DOMException('Navigation cancelled request','AbortError')),{once:true}))
 }
 return nativeFetch.call(this,url,options)
}
const NativeContext=window.AudioContext
window.AudioContext=class extends NativeContext {
 constructor(...args){
  super(...args)
  const record={context:this,oscillators:[],levels:[]}
  window.__audio.push(record)
  // Deterministic policy injection for the fallback test; nodes stay native.
  if(window.__simulateAutoplayBlock){
   this.suspend()
   const resume=this.resume.bind(this)
   this.resume=()=>window.__allowRingtoneResume?resume():Promise.reject(new DOMException('Autoplay blocked for test','NotAllowedError'))
  }
  const createOscillator=this.createOscillator.bind(this)
  this.createOscillator=()=>{
   const oscillator=createOscillator(),node={started:0,stopped:0,disconnected:0}
   record.oscillators.push(node)
   for(const method of ['start','stop','disconnect']){
    const native=oscillator[method].bind(oscillator)
    oscillator[method]=(...values)=>{node[{start:'started',stop:'stopped',disconnect:'disconnected'}[method]]++;return native(...values)}
   }
   return oscillator
  }
  const createGain=this.createGain.bind(this)
  this.createGain=()=>{
   const gain=createGain()
   for(const method of ['setValueAtTime','linearRampToValueAtTime']){
    const native=gain.gain[method].bind(gain.gain)
    gain.gain[method]=(...values)=>{record.levels.push(values[0]);return native(...values)}
   }
   return gain
  }
 }
}
