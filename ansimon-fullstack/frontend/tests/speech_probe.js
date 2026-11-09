// Deterministic speech events for sequencing/STT tests; no claim of audio quality.
window.__tts={calls:[],pending:null,auto:false,finish(){const speech=this.pending;this.pending=null;speech?.onend?.()},fail(){const speech=this.pending;this.pending=null;speech?.onerror?.()}}
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
 speak(speech){window.__tts.calls.push(speech.text);window.__tts.pending=speech;if(window.__tts.auto)setTimeout(()=>{if(window.__tts.pending===speech)window.__tts.finish()},0)},
 cancel(){window.__tts.pending=null}
}})
window.__recognitionSessions=[]
window.SpeechRecognition=class {
 constructor(){window.__recognitionSessions.push(this)}
 start(){window.__recognition=this;if(window.__throwRecognitionStart)throw Object.assign(new Error('start failed'),{name:window.__throwRecognitionStart});if(!window.__deferRecognitionStart)this.onstart?.()}
 emitFinal(text){const result=Object.assign([{transcript:text}],{isFinal:true});this.onresult?.({resultIndex:0,results:[result]})}
 emitInterim(text){const result=Object.assign([{transcript:text}],{isFinal:false});this.onresult?.({resultIndex:0,results:[result]})}
 emitError(error){this.onerror?.({error})}
 stop(){this.onend?.()}
 abort(){this.aborted=true}
}
