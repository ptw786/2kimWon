import test from 'node:test'
import assert from 'node:assert/strict'
import {api,post} from '../src/api.js'

async function withFetch(fake,run){const previous=globalThis.fetch;globalThis.fetch=fake;try{await run()}finally{globalThis.fetch=previous}}
function pending(signal){return new Promise((_resolve,reject)=>signal?.addEventListener('abort',()=>reject(new DOMException('aborted','AbortError')),{once:true}))}
async function outcome(request){let timer;try{return await Promise.race([request.then(()=> 'UNEXPECTED_SUCCESS',error=>error.message),new Promise(resolve=>{timer=setTimeout(()=>resolve('STILL_PENDING_WITHOUT_TIMEOUT'),150)})])}finally{clearTimeout(timer)}}

test('fetch deadline yields an actionable timeout instead of waiting forever',async()=>{
 await withFetch((_url,options)=>pending(options.signal),async()=>{
  assert.match(await outcome(api('/residents',{timeoutMs:20})),/요청 시간이 초과/)
 })
})
test('response-body deadline also protects a POST already committed by the server',async()=>{
 await withFetch(async(_url,options)=>({ok:true,status:201,json:()=>pending(options.signal)}),async()=>{
  assert.match(await outcome(post('/calls/1/turns',{answer:'안 아파',index:0,attempt:0},undefined,{timeoutMs:20})),/요청 시간이 초과/)
 })
})
test('caller cancellation stays cancellation, not a misleading connection failure',async()=>{
 await withFetch((_url,options)=>pending(options.signal),async()=>{
  const controller=new AbortController(),request=api('/calls',{signal:controller.signal})
  controller.abort()
  await assert.rejects(request,error=>error.name==='AbortError')
 })
})
test('POST preserves exact payload and idempotency key',async()=>{
 await withFetch(async(url,options)=>{
  assert.equal(url,'/api/calls/1/turns');assert.equal(options.headers['Idempotency-Key'],'same-request')
  assert.equal(options.headers['Content-Type'],'application/json')
  assert.deepEqual(JSON.parse(options.body),{answer:'안 아파',index:0,attempt:0})
  return {ok:true,status:201,json:async()=>({count:1})}
 },async()=>assert.deepEqual(await post('/calls/1/turns',{answer:'안 아파',index:0,attempt:0},'same-request'),{count:1}))
})
test('HTTP 500 is never converted into a successful fake response',async()=>{
 await withFetch(async()=>({ok:false,status:500,json:async()=>({detail:'데이터베이스 오류'})}),async()=>{
  await assert.rejects(api('/dashboard'),/\/api\/dashboard \(500\): 데이터베이스 오류/)
 })
})
test('non-JSON success and structured 422 validation errors are explained',async()=>{
 await withFetch(async()=>({ok:true,status:200,json:async()=>{throw Error('not JSON')}}),async()=>{await assert.rejects(api('/calls'),/올바른 JSON/)} )
 await withFetch(async()=>({ok:false,status:422,json:async()=>({detail:[{loc:['body','answer'],msg:'required'}]})}),async()=>{await assert.rejects(api('/calls'),/body.answer: required/)})
})
