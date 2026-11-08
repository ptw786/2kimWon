export async function api(path, options={}) {
  const url = '/api'+path
  let response
  try {
    response = await fetch(url, {...options, headers:{'Content-Type':'application/json', ...options.headers}})
  } catch(e) {
    if(options.signal?.aborted)throw e
    throw Error(`${url}: 백엔드 서버에 연결할 수 없습니다. FastAPI의 8000번 포트 실행 상태를 확인하세요.`)
  }
  const data = await response.json().catch(()=>null)
  if (!response.ok) {
    const detail = typeof data?.detail === 'string' ? data.detail
      : Array.isArray(data?.detail) ? data.detail.map(e=>`${e.loc?.join('.')}: ${e.msg}`).join(' / ')
      : response.status >= 500 ? '백엔드 실행 상태와 터미널 로그를 확인하세요. Vite 프록시 연결 또는 서버 내부 오류일 수 있습니다.' : '요청을 처리할 수 없습니다.'
    throw Error(`${url} (${response.status}): ${detail}`)
  }
  if (data === null) throw Error(`${url}: 서버 응답이 올바른 JSON이 아닙니다. API 주소와 프록시 설정을 확인하세요.`)
  return data
}
export const post=(path, body={}, key, options={})=>api(path,{...options,method:'POST',body:JSON.stringify(body),headers:{...options.headers,...(key?{'Idempotency-Key':key}:{})}})
