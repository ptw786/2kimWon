import {test} from 'node:test'
import assert from 'node:assert/strict'
import {saveDraft,resolveDraft,clearDraft,discardRecovered} from '../src/drafts.js'
const storage=()=>{const m=new Map();return {getItem:k=>m.get(k)??null,setItem:(k,v)=>m.set(k,v),removeItem:k=>m.delete(k)}}
const detail=(count=0,attempt=0,attempts=[])=>({id:1,status:'in_progress',turns:[],attempts,dialogue_state:{count,attempt}})
const draft={answer:'몸이 괜찮아',index:0,attempt:0,question:'몸 상태',source:'text',pending:false}
test('draft restores only to its own call and exact question/attempt',()=>{
 const s=storage();assert.equal(saveDraft(s,1,draft),true)
 assert.equal(resolveDraft(s,detail()).answer,draft.answer)
 assert.equal(resolveDraft(s,{...detail(),id:2}).answer,'')
})
test('unconfirmed submission restores exact retry body',()=>{
 const s=storage();saveDraft(s,1,{...draft,pending:true,source:'stt'})
 assert.deepEqual(resolveDraft(s,detail()).pending,{answer:draft.answer,index:0,attempt:0,engine:'hybrid',source:'stt'})
})
test('committed answer with lost response is not resubmitted on refresh',()=>{
 const s=storage();saveDraft(s,1,{...draft,pending:true})
 const d=detail(1,0,[{question_index:0,attempt:0,answer:draft.answer}])
 assert.equal(resolveDraft(s,d).answer,'');assert.equal(resolveDraft(s,d).pending,null)
 assert.equal(s.getItem('ansimon:draft:1'),null)
})
test('different answer from another tab is preserved separately, never sent to the next question',()=>{
 const s=storage();saveDraft(s,1,{...draft,pending:true})
 const d=detail(1,0,[{question_index:0,attempt:0,answer:'다른 답변'}])
 const r=resolveDraft(s,d);assert.equal(r.answer,'');assert.equal(r.pending,null)
 assert.equal(r.recoveredDraft.answer,draft.answer)
 assert.equal(resolveDraft(s,d).recoveredDraft.answer,draft.answer)
})
test('same basic question with a different retry attempt also isolates old drafts',()=>{
 const s=storage();saveDraft(s,1,draft)
 const r=resolveDraft(s,detail(0,1));assert.equal(r.answer,'');assert.equal(r.recoveredDraft.answer,draft.answer)
})
test('blocked storage never breaks answer submission',()=>{
 const s={setItem:()=>{throw Error('blocked')},getItem:()=>{throw Error('blocked')},removeItem:()=>{throw Error('blocked')}}
 assert.equal(saveDraft(s,1,draft),false);assert.equal(resolveDraft(s,detail()).answer,'')
 assert.doesNotThrow(()=>clearDraft(s,1,true));assert.equal(saveDraft(null,1,draft),false)
})
test('ending/discarding clears drafts without affecting another call',()=>{
 const s=storage();saveDraft(s,1,draft);saveDraft(s,2,draft)
 resolveDraft(s,detail(1));discardRecovered(s,1);assert.equal(resolveDraft(s,detail(1)).recoveredDraft,null)
 clearDraft(s,2,true);assert.equal(s.getItem('ansimon:draft:2'),null)
})
