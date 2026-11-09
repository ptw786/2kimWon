/** Event-driven output with one utterance and stable per-dialogue-stage keys. */
export class SpeechOutput {
  constructor({host,beforeSpeak,onState,onNotice,enabled}){
    Object.assign(this,{host,beforeSpeak,onState,onNotice,enabled})
    this.task=null;this.completed=new Set();this.disposed=false
  }
  speak(text,key=text){
    if(this.disposed)return Promise.resolve(false)
    if(!text||!this.enabled())return Promise.resolve(true)
    if(this.task?.key===key)return this.task.promise
    if(this.completed.has(key))return Promise.resolve(true)
    this.stop(false)
    this.beforeSpeak() // Always close STT, even if a caller forgot to do so.
    const synthesis=this.host.speechSynthesis,Utterance=this.host.SpeechSynthesisUtterance
    if(!synthesis||!Utterance){this.completed.add(key);this.onNotice('음성 출력을 지원하지 않아 화면의 글로 안내합니다.');return Promise.resolve(true)}
    let resolve
    const promise=new Promise(done=>{resolve=done})
    const task={key,promise,resolve,timer:null,utterance:null}
    this.task=task
    const settle=proceed=>{
      if(this.task!==task)return
      this.host.clearTimeout(task.timer)
      if(task.utterance){task.utterance.onend=null;task.utterance.onerror=null}
      this.task=null
      if(proceed)this.completed.add(key)
      if(!this.disposed)this.onState({speaking:false,speakingText:''})
      resolve(proceed)
    }
    task.settle=settle
    try{
      const speech=new Utterance(text);task.utterance=speech
      speech.lang='ko-KR';speech.rate=.86
      const voice=synthesis.getVoices?.().find(voice=>/^ko(?:-|$)/i.test(voice.lang))
      if(voice)speech.voice=voice
      speech.onend=()=>settle(true)
      speech.onerror=()=>{if(this.task===task){this.onNotice('음성을 재생하지 못해 화면의 글로 안내합니다.');settle(true)}}
      task.timer=this.host.setTimeout(()=>{
        if(this.task!==task)return
        this.onNotice('음성 응답이 지연되어 화면의 글로 안내합니다.')
        settle(true);synthesis.cancel()
      },Math.min(60000,Math.max(8000,text.length*450)))
      this.onState({speaking:true,speakingText:text})
      synthesis.speak(speech)
    }catch{this.onNotice('음성을 재생하지 못해 화면의 글로 안내합니다.');settle(true);try{synthesis.cancel()}catch{}}
    return promise
  }
  stop(continueSequence=false){
    this.task?.settle(continueSequence)
    try{this.host.speechSynthesis?.cancel()}catch{}
  }
  dispose(){this.disposed=true;this.stop(false);this.completed.clear()}
}
