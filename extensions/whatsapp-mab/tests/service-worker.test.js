import test from 'node:test';
import assert from 'node:assert/strict';
let listener;
const opened=[];
globalThis.chrome={runtime:{id:'test-extension',getURL:path=>`chrome-extension://test-extension/${path}`,onMessage:{addListener:fn=>{listener=fn;}}},action:{onClicked:{addListener(){}},setBadgeText:async()=>{},setTitle:async()=>{}},storage:{session:{get:async()=>({settings:{apiKey:'BACKGROUND-ONLY-TEST',apiBase:'http://localhost:8000',webBase:'http://localhost:3100'}}),set:async()=>{}}},tabs:{create:async value=>opened.push(value)}};
await import('../service-worker.js');
const trusted={id:'test-extension',url:'https://web.whatsapp.com/'};
const invoke=(message,sender=trusted)=>new Promise(resolve=>{const active=listener(message,sender,resolve);if(active!==true)resolve(null);});
test('RPC rejeita origem alheia, extensão diferente e tipo desconhecido',async()=>{
 assert.equal(await invoke({type:'mab:settings'},{...trusted,url:'https://evil.example/'}),null);
 assert.equal(await invoke({type:'mab:settings'},{...trusted,id:'other-extension'}),null);
 assert.equal(await invoke({type:'unrelated'}),null);
});
test('RPC público não revela credenciais e abre só configuração interna',async()=>{
 const result=await invoke({type:'mab:settings'});assert.equal(result.ok,true);assert.equal(result.value.hasApiKey,true);assert.ok(!JSON.stringify(result).includes('BACKGROUND-ONLY-TEST'));
 const openedResult=await invoke({type:'mab:open-settings'});assert.equal(openedResult.ok,true);assert.equal(opened.at(-1).url,'chrome-extension://test-extension/options.html');
});
