// Deterministic speech events for sequencing/STT tests; no claim of audio quality.
window.__tts={calls:[],pending:null,auto:false,finish(){const speech=this.pending;this.pending=null;speech?.onend?.()},fail(){const speech=this.pending;this.pending=null;speech?.onerror?.()}}
Object.defineProperty(window,'speechSynthesis',{configurable:true,value:{
 speak(speech){window.__tts.calls.push(speech.text);window.__tts.pending=speech;if(window.__tts.auto)setTimeout(()=>{if(window.__tts.pending===speech)window.__tts.finish()},0)},
 cancel(){window.__tts.pending=null}
}})
window.SpeechRecognition=class {
 start(){window.__recognition=this}
 stop(){this.onend?.()}
 abort(){this.aborted=true}
}
