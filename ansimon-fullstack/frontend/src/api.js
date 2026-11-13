export const API_TIMEOUT_MS=15000

export async function api(path, options={}) {
  const url='/api'+path
  const {signal:callerSignal,timeoutMs=API_TIMEOUT_MS,...requestOptions}=options
  const controller=new AbortController()
  let timedOut=false,response
  const cancel=()=>controller.abort(callerSignal?.reason)
  if(callerSignal?.aborted)cancel()
  else callerSignal?.addEventListener('abort',cancel,{once:true})
  const timer=setTimeout(()=>{timedOut=true;controller.abort()},timeoutMs)
  try {
    response=await fetch(url,{...requestOptions,signal:controller.signal,headers:{'Content-Type':'application/json',...requestOptions.headers}})
    const data=await response.json().catch(error=>{
      if(controller.signal.aborted)throw error
      return null
    })
    if(!response.ok){
      const detail=typeof data?.detail==='string'?data.detail
        :Array.isArray(data?.detail)?data.detail.map(e=>`${e.loc?.join('.')}: ${e.msg}`).join(' / ')
        :response.status>=500?'백엔드 실행 상태와 터미널 로그를 확인하세요. Vite 프록시 연결 또는 서버 내부 오류일 수 있습니다.':'요청을 처리할 수 없습니다.'
      const error=Error(`${url} (${response.status}): ${detail}`)
      error.status=response.status;error.detail=data?.detail;error.url=url
      throw error
    }
    if(data===null)throw Error(`${url}: 서버 응답이 올바른 JSON이 아닙니다. API 주소와 프록시 설정을 확인하세요.`)
    return data
  }catch(error){
    if(callerSignal?.aborted)throw error
    if(timedOut)throw Error(`${url}: 요청 시간이 초과되었습니다. 저장 여부를 확인하지 못했습니다. 입력한 답변을 그대로 두고 다시 시도하세요.`)
    if(!response)throw Error(`${url}: 백엔드 서버에 연결할 수 없습니다. FastAPI의 8000번 포트 실행 상태를 확인하세요.`)
    throw error
  }finally{
    clearTimeout(timer)
    callerSignal?.removeEventListener('abort',cancel)
  }
}
export const post=(path,body={},key,options={})=>api(path,{...options,method:'POST',body:JSON.stringify(body),headers:{...options.headers,...(key?{'Idempotency-Key':key}:{})}})
