export function ErrorNotice({error,retry,busy=false}){
  return error?<div className="error" role="alert">{error}{retry&&<button disabled={busy} onClick={retry}>다시 시도</button>}</div>:null
}
export function Loading({loading}){
  return loading?<div className="loading" role="status">서버 데이터를 불러오는 중...</div>:null
}
