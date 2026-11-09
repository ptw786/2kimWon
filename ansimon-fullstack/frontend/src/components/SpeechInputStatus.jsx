export default function SpeechInputStatus({sttStatus,sttError,sttNotice,lastTranscript,interimTranscript,sttSupported}){
 return <div className="speech-input-status" data-stt-status={sttStatus}>
  {sttError&&<p className="speech-error" role="alert">{sttError}</p>}
  {!sttError&&<p role="status">{sttSupported===false?'이 브라우저에서는 텍스트로 답변해 주세요.':sttNotice||'마이크를 켜서 말씀하시거나 아래에 답변을 입력해 주세요.'}</p>}
  {interimTranscript&&<p className="transcript interim" aria-live="polite"><b>인식 중:</b> {interimTranscript}</p>}
  {lastTranscript&&<p className="transcript" aria-live="polite"><b>최근 인식 결과:</b> {lastTranscript}</p>}
 </div>
}
