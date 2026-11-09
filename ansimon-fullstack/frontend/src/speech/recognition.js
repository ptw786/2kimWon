const ERRORS = {
  'not-allowed': '마이크 사용 권한이 거부되었습니다. 주소창에서 마이크 권한을 허용하거나 텍스트로 답변해 주세요.',
  'service-not-allowed': '브라우저의 음성 인식 서비스를 사용할 수 없습니다. 텍스트로 답변해 주세요.',
  'audio-capture': '사용할 수 있는 마이크를 찾지 못했습니다. 마이크 연결을 확인하거나 텍스트로 답변해 주세요.',
  'no-speech': '음성을 인식하지 못했습니다. 다시 말하거나 텍스트로 답변해 주세요.',
  network: '음성 인식 서비스에 연결할 수 없습니다. 텍스트로 답변해 주세요.',
  aborted: '음성 입력이 중단되었습니다. 다시 시작하거나 텍스트로 답변해 주세요.',
  'language-not-supported': '이 브라우저에서 한국어 음성 인식을 사용할 수 없습니다. 텍스트로 답변해 주세요.',
}
export const recognitionMessage = code => ERRORS[code] || '음성 인식에 실패했습니다. 다시 시작하거나 텍스트로 답변해 주세요.'

/** Owns exactly one recognition session, including the time before onstart. */
export class SpeechInput {
  constructor({host,canStart,onState,onFinal,timeout=30000}) {
    Object.assign(this,{host,canStart,onState,onFinal,timeout})
    this.session=null;this.disposed=false
  }
  get supported(){return Boolean(this.host.SpeechRecognition||this.host.webkitSpeechRecognition)}
  get active(){return this.session!==null}
  emit(state){if(!this.disposed)this.onState(state)}
  close(session){
    if(this.session!==session)return
    this.session=null
    this.host.clearTimeout(session.timer)
    const rec=session.rec
    rec.onstart=null;rec.onresult=null;rec.onerror=null;rec.onend=null;rec.onnomatch=null
    try{rec.abort()}catch{}
  }
  fail(session,code){
    if(this.session!==session||this.disposed)return
    this.close(session)
    this.emit({sttStatus:'idle',listening:false,interimTranscript:'',sttError:recognitionMessage(code),sttNotice:''})
  }
  start(){
    if(this.disposed||this.active||!this.canStart())return false
    const Recognition=this.host.SpeechRecognition||this.host.webkitSpeechRecognition
    if(!Recognition){this.emit({sttError:'이 브라우저는 음성 인식을 지원하지 않습니다. 텍스트로 답변해 주세요.',sttNotice:'',sttStatus:'idle',listening:false});return false}
    if(this.host.isSecureContext===false){this.emit({sttError:'마이크는 HTTPS 또는 localhost에서 사용할 수 있습니다. 텍스트로 답변해 주세요.'});return false}
    let session
    try{
      const rec=new Recognition()
      session={rec,timer:null}
      this.session=session
      rec.lang='ko-KR';rec.continuous=false;rec.interimResults=true;rec.maxAlternatives=1
      const live=()=>!this.disposed&&this.session===session
      // Lock synchronously: a second click before onstart cannot open another mic.
      this.emit({sttStatus:'starting',listening:true,interimTranscript:'',lastTranscript:'',sttError:'',sttNotice:'마이크를 연결하고 있습니다.'})
      rec.onstart=()=>{if(live())this.emit({sttStatus:'listening',listening:true,sttNotice:'듣고 있습니다. 답변을 말씀해 주세요.'})}
      rec.onresult=event=>{
        if(!live())return
        const final=[],interim=[]
        for(let i=event.resultIndex||0;i<event.results.length;i++){
          const result=event.results[i],text=result?.[0]?.transcript||''
          if(result.isFinal===true)final.push(text)
          else interim.push(text)
        }
        if(final.join(' ').trim()){
          const text=final.join(' ').trim()
          this.close(session) // Detach and abort before any TTS/API processing.
          this.emit({sttStatus:'idle',listening:false,interimTranscript:'',lastTranscript:text,sttError:'',sttNotice:'음성 인식이 완료되었습니다.'})
          this.onFinal(text)
        }else if(interim.join(' ').trim())this.emit({interimTranscript:interim.join(' ').trim()})
      }
      rec.onerror=event=>this.fail(session,event.error)
      rec.onnomatch=()=>this.fail(session,'no-speech')
      rec.onend=()=>{if(live())this.fail(session,'no-speech')}
      session.timer=this.host.setTimeout(()=>this.fail(session,'no-speech'),this.timeout)
      rec.start()
      return true
    }catch(error){
      if(session)this.close(session)
      const code=['NotAllowedError','SecurityError'].includes(error.name)?'not-allowed':'start-failed'
      this.emit({sttStatus:'idle',listening:false,interimTranscript:'',sttError:recognitionMessage(code),sttNotice:''})
      return false
    }
  }
  stop({manual=false}={}){
    const session=this.session
    if(!session)return
    this.close(session)
    this.emit({sttStatus:'idle',listening:false,interimTranscript:'',sttNotice:manual?'음성 입력을 중지했습니다. 텍스트로 답변할 수 있습니다.':'',...(manual?{sttError:''}:{})})
  }
  dispose(){this.disposed=true;if(this.session)this.close(this.session)}
}
