import test from 'node:test';
import assert from 'node:assert/strict';
import { LocalMabClient } from '../background-client.js';
const id='fdf70ad9-1f78-4a96-903c-d2312383fd67';
const capture={captureId:id,messages:[{sourceId:'1',role:'customer',text:'Aceitam Pix?'}]};
const choices={targetSourceId:'1',architectureMode:'centralized_orchestration',runtimeMode:'real'};
const settings=()=>({apiBase:'http://127.0.0.1:8000',webBase:'http://127.0.0.1:3100',apiKey:'LOCAL-TEST-KEY'});
test('credencial é acrescentada somente no background e nunca no retorno público',async()=>{
 const calls=[];const client=new LocalMabClient({getSettings:settings,fetchImpl:async(url,opts)=>{calls.push({url,opts});return{ok:true,json:async()=>({conversationId:id,runIds:[id]})};}});
 assert.deepEqual(await client.publicSettings(),{apiBase:'http://127.0.0.1:8000',webBase:'http://127.0.0.1:3100',hasApiKey:true});
 const imported=await client.importCapture(capture,choices);assert.equal(imported.conversationId,id);
 assert.equal(calls[0].opts.headers['X-API-Key'],'LOCAL-TEST-KEY');assert.ok(!calls[0].opts.body.includes('LOCAL-TEST-KEY'));
 assert.equal(JSON.parse(calls[0].opts.body).captureId,id);
});
test('retries conservam UUID e corpo e recusam papel desconhecido antes da rede',async()=>{
 const bodies=[];const client=new LocalMabClient({getSettings:settings,fetchImpl:async(_,opts)=>{bodies.push(opts.body);return{ok:true,json:async()=>({conversationId:id,runIds:[id]})};}});
 await client.importCapture(capture,choices);await client.importCapture(capture,choices);assert.equal(bodies[0],bodies[1]);
 await assert.rejects(()=>client.importCapture({...capture,messages:[{sourceId:'1',role:'unknown',text:'Oi'}]},choices),/quem enviou/);assert.equal(bodies.length,2);
});
test('401 e erro de rede preservam erro útil sem retornar a chave',async()=>{
 const denied=new LocalMabClient({getSettings:settings,fetchImpl:async()=>({ok:false,status:401,json:async()=>({})})});await assert.rejects(()=>denied.importCapture(capture,choices),/chave da API/);
 const offline=new LocalMabClient({getSettings:settings,fetchImpl:async()=>{throw new TypeError('Failed to fetch');}});await assert.rejects(()=>offline.importCapture(capture,choices),/alcançar o MAB/);
});
test('polling é GET, valida UUID e devolve apenas projeção dos runs pedidos',async()=>{
 const calls=[];const client=new LocalMabClient({getSettings:settings,fetchImpl:async(url,options)=>{calls.push({url,options});return{ok:true,json:async()=>({runs:[{id,status:'completed'}],messages:[]})};}});
 const result=await client.progress(id,[id]);assert.equal(result.finished,true);assert.equal(calls[0].options.method,undefined);assert.equal(calls[0].url,`http://127.0.0.1:8000/conversations/${id}`);
 await assert.rejects(()=>client.progress('../secret',[id]),/identificador/);
 assert.equal(calls.length,1);
});

test('fetch padrão mantém receptor global exigido pelo navegador em vez da instância do cliente',async()=>{
 const original=globalThis.fetch, calls=[];
 try{
  globalThis.fetch=function(url,options){
   if(this!==globalThis)throw new TypeError('Illegal invocation');
   calls.push({url,options});return Promise.resolve({ok:true,json:async()=>({conversationId:id,runIds:[id]})});
  };
  const client=new LocalMabClient({getSettings:settings});
  const result=await client.importCapture(capture,choices);assert.equal(result.conversationId,id);assert.equal(calls.length,1);assert.equal(calls[0].options.method,'POST');
 }finally{globalThis.fetch=original;}
});
