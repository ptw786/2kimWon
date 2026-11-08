import {useCallback,useEffect,useRef,useState} from 'react'

export function useResource(loader) {
  const [data,setData]=useState(null),[error,setError]=useState(''),[loading,setLoading]=useState(true)
  const controller=useRef(null)
  const reload=useCallback(async()=>{
    controller.current?.abort()
    const request=new AbortController()
    controller.current=request
    setLoading(true);setError('')
    try {
      const result=await loader(request.signal)
      if(!request.signal.aborted)setData(result)
    } catch(e) {
      if(!request.signal.aborted)setError(e.message)
    } finally {
      if(!request.signal.aborted)setLoading(false)
    }
  },[loader])
  useEffect(()=>{reload();return()=>controller.current?.abort()},[reload])
  return {data,error,loading,reload}
}
