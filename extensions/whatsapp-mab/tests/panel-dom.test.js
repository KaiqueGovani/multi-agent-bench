import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';
import {webcrypto} from 'node:crypto';
const id='fdf70ad9-1f78-4a96-903c-d2312383fd67';
const html='<html><body><div id="main"><header>Conversa fictícia</header><div data-id="one"><div aria-label="Conversa fictícia:"></div><div data-pre-plain-text="[15:04] Conversa fictícia: "><span class="selectable-text">Aceitam Pix?</span></div></div><div data-id="two"><div aria-label="Você:"></div><span class="selectable-text">Vou conferir.</span></div></div></body></html>';
function setup(progress){
 const {window,document}=parseHTML(html);const calls=[],copied=[],timers=[];
 const context=vm.createContext({document,MutationObserver:window.MutationObserver,crypto:webcrypto,navigator:{clipboard:{writeText:async text=>copied.push(text)}},setTimeout:(fn,delay)=>{timers.push({fn,delay});return timers.length;},clearTimeout(){},chrome:{runtime:{sendMessage:async message=>{calls.push(message);return{ok:true,value:message.type==='mab:settings'?{apiBase:'http://localhost:8000',hasApiKey:true}:message.type==='mab:import'?{conversationId:id,runIds:[id]}:progress};}}}});
 for(const file of ['extractor.js','panel-core.js','panel.js'])vm.runInContext(fs.readFileSync(new URL(`../${file}`,import.meta.url),'utf8'),context);
 context.MabWhatsAppPanel.toggle();return{context,window,document,calls,copied,timers,root:document.getElementById('mab-whatsapp-assistant').shadowRoot};
}
function click(window,node,trusted=false){const event=new window.Event('click',{bubbles:true});Object.defineProperty(event,'isTrusted',{value:trusted});node.dispatchEvent(event);}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
test('abre painel dentro da conversa, sem aba nova ou envio automático',async()=>{
 const s=setup();await flush();assert.equal(s.root.getElementById('chat').textContent,'Conversa fictícia');assert.equal(s.root.getElementById('target').value,'Aceitam Pix?');
 assert.deepEqual(s.calls.map(c=>c.type),['mab:settings']);assert.ok(s.root.innerHTML.includes('Nada é enviado ao WhatsApp.'));assert.ok(!s.root.querySelector('input[type=password]'));
 click(s.window,s.root.getElementById('generate'));await flush();assert.equal(s.calls.filter(c=>c.type==='mab:import').length,0,'click programático não dispara processamento');
});
test('processa por clique explícito, mostra resposta inline e copia somente por clique',async()=>{
 const s=setup({runs:[{id,name:'Centralizada',status:'completed',text:'Aceitamos Pix no contexto simulado.',finished:true,tokens:123,durationMs:1000}],finished:true,ready:1});
 click(s.window,s.root.getElementById('generate'),true);await flush();await flush();
 assert.equal(s.calls.filter(c=>c.type==='mab:import').length,1);assert.equal(s.root.getElementById('response').textContent,'Aceitamos Pix no contexto simulado.');assert.deepEqual(s.copied,[]);
 click(s.window,s.root.getElementById('copy'),true);await flush();assert.deepEqual(s.copied,['Aceitamos Pix no contexto simulado.']);
 assert.equal(s.calls.filter(c=>c.type==='mab:open-details').length,0,'não abre MAB sem pedido');
});
test('troca para conversa com mesmo nome mas IDs diferentes invalida contexto e resposta',async()=>{
 const s=setup({runs:[{id,name:'Centralizada',status:'completed',text:'Resposta antiga',finished:true}],finished:true,ready:1});
 click(s.window,s.root.getElementById('generate'),true);await flush();await flush();
 s.document.querySelector('[data-id="one"]').setAttribute('data-id','other1');s.document.querySelector('[data-id="two"]').setAttribute('data-id','other2');
 // Attribute changes are intentionally not observed; a real chat switch also
 // replaces messages. This mutation reproduces that structural transition.
 s.document.getElementById('main').append(s.document.createElement('div'));await flush();
 assert.equal(s.root.getElementById('results').hidden,true);assert.equal(s.root.getElementById('generate').disabled,true);assert.equal(s.root.getElementById('target').value,'');
});
test('fechar painel invalida resposta assíncrona em andamento',async()=>{
 const s=setup();let resolveImport;
 s.context.chrome.runtime.sendMessage=message=>{s.calls.push(message);if(message.type==='mab:import')return new Promise(resolve=>{resolveImport=resolve;});return Promise.resolve({ok:true,value:{}});};
 click(s.window,s.root.getElementById('generate'),true);await flush();click(s.window,s.root.getElementById('close'));resolveImport({ok:true,value:{conversationId:id,runIds:[id]}});await flush();
 assert.equal(s.root.getElementById('panel').hidden,true);assert.equal(s.calls.filter(c=>c.type==='mab:progress').length,0);
});
