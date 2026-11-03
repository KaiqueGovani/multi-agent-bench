import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';
import {webcrypto} from 'node:crypto';
const id='fdf70ad9-1f78-4a96-903c-d2312383fd67';
const message=(id,sender,text)=>`<div data-id="${id}"><div style="display:flex"><div aria-label="${sender}:"></div><div data-pre-plain-text="[15:04] ${sender}: "><span class="selectable-text">${text}</span></div></div></div>`;
const main=()=>`<div id="main"><header>Conversa fictícia</header>${message('a','Conversa fictícia','Olá')}${message('b','Você','Como posso ajudar?')}${message('c','Conversa fictícia','Aceitam Pix?')}${message('d','Conversa fictícia','MENSAGEM FUTURA')}<div data-id="media"><div aria-label="Conversa fictícia:"></div><img src="blob:fake"></div><footer><div contenteditable="true" aria-label="Campo de composição conta A"></div></footer></div>`;
function setup(options={}){
 const {window,document}=parseHTML(`<html><body>${main()}</body></html>`);const calls=[],copied=[];
 const context=vm.createContext({document,MutationObserver:window.MutationObserver,crypto:webcrypto,navigator:{clipboard:{writeText:async text=>copied.push(text)}},setTimeout:options.setTimeout||setTimeout,clearTimeout:options.clearTimeout||clearTimeout,Date:options.Date||Date,chrome:{runtime:{sendMessage:async request=>{calls.push(request);return{ok:true,value:request.type==='mab:import'?{conversationId:id,runIds:[id]}:{runs:[{id,name:'Centralizada',status:'completed',text:'Aceitamos Pix no contexto controlado.',finished:true}],finished:true,ready:1}};}}}});
 for(const file of ['extractor.js','panel-core.js','message-actions.js'])vm.runInContext(fs.readFileSync(new URL(`../${file}`,import.meta.url),'utf8'),context);
 context.MabWhatsAppMessages.toggle();
 return{window,document,context,calls,copied,host:(source)=>document.querySelector(`[data-id="${source}"] > [data-mab-ui="message-action"]`),close:()=>context.MabWhatsAppMessages.toggle()};
}
function click(s,node,trusted=true){const event=new s.window.Event('click',{bubbles:true});Object.defineProperty(event,'isTrusted',{value:trusted});node.dispatchEvent(event);}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
const settle=()=>new Promise(resolve=>setTimeout(resolve,90));
function open(s,source){const shadow=s.host(source).shadowRoot;click(s,shadow.querySelector('.action'));return shadow;}
function field(shadow,id){return shadow.getElementById(id)||shadow.host.querySelector(`[data-mab-control="${id}"]`);}
function select(shadow,id,value){const select=field(shadow,id);for(const option of select.querySelectorAll('option'))option.selected=option.value===value;select.dispatchEvent(new select.ownerDocument.defaultView.Event('change',{bubbles:true}));}

test('ações aparecem só sob mensagens recebidas de texto; ativação não consulta API',async()=>{
 const s=setup();assert.ok(s.host('a'));assert.ok(s.host('c'));assert.ok(s.host('d'));assert.equal(s.host('b'),null);assert.equal(s.host('media'),null);assert.equal(s.calls.length,0);
 assert.equal(s.document.querySelectorAll('[data-mab-ui]').length,3);assert.equal(s.document.querySelector('#mab-whatsapp-assistant'),null);
 click(s,s.host('c').shadowRoot.querySelector('.action'),false);assert.equal(s.host('c').shadowRoot.querySelector('section'),null,'click programático não abre ação privilegiada');s.close();
});
test('clique abre cartão abaixo da mensagem escolhida, geração só no segundo clique e corta futuro',async()=>{
 const s=setup(),shadow=open(s,'c');assert.ok(shadow.querySelector('section'));assert.equal(s.calls.length,0);
 select(shadow,'architecture','centralized_orchestration');select(shadow,'context','recent');select(shadow,'runtime','real');
 click(s,shadow.getElementById('generate'));await flush();await flush();
 const imported=s.calls.find(request=>request.type==='mab:import');assert.deepEqual(Array.from(imported.capture.messages,m=>m.sourceId),['a','b','c']);assert.equal(imported.choices.targetSourceId,'c');assert.ok(!JSON.stringify(imported).includes('MENSAGEM FUTURA'));
 assert.equal(shadow.getElementById('response').textContent,'Aceitamos Pix no contexto controlado.');assert.deepEqual(s.copied,[]);
 click(s,shadow.getElementById('copy'));await flush();assert.deepEqual(s.copied,['Aceitamos Pix no contexto controlado.']);assert.equal(s.calls.filter(request=>request.type==='mab:open-details').length,0);s.close();
});
test('ajuste textual e contexto somente alvo produzem uma única entrada',async()=>{
 const s=setup(),shadow=open(s,'c');select(shadow,'architecture','all_architectures');select(shadow,'context','target');select(shadow,'runtime','real');field(shadow,'target').value='Consulta sintética de estoque';
 click(s,shadow.getElementById('generate'));await flush();await flush();const request=s.calls.find(r=>r.type==='mab:import');
 assert.equal(request.capture.messages.length,1);assert.equal(request.capture.messages[0].sourceId,'c');assert.equal(request.capture.messages[0].text,'Consulta sintética de estoque');assert.equal(request.choices.architectureMode,'all_architectures');s.close();
});
test('apenas um cartão aberto, ações continuam em cada mensagem',()=>{
 const s=setup(),first=open(s,'a'),second=open(s,'c');assert.equal(first.querySelector('section'),null);assert.ok(second.querySelector('section'));assert.equal(s.document.querySelectorAll('[data-mab-ui="message-action"]').length,3);s.close();
});
test('novas mensagens renderizadas recebem ação e virtualização remove cartão antigo',async()=>{
 const s=setup();open(s,'c');const holder=s.document.createElement('div');holder.innerHTML=message('new','Conversa fictícia','Nova pergunta');s.document.getElementById('main').append(holder.firstChild);await settle();assert.ok(s.host('new'));
 s.document.querySelector('[data-id="c"]').remove();await settle();assert.equal(s.host('c'),null);assert.ok(s.host('new'));assert.equal(s.calls.length,0);s.close();
});
test('troca de identidade limpa cartão e bloqueia resposta assíncrona antiga',async()=>{
 const s=setup(),shadow=open(s,'c');let resolveImport;
 s.context.chrome.runtime.sendMessage=request=>{s.calls.push(request);if(request.type==='mab:import')return new Promise(resolve=>{resolveImport=resolve;});return Promise.resolve({ok:true,value:{}});};
 click(s,shadow.getElementById('generate'));await flush();s.document.querySelector('footer [contenteditable]').setAttribute('aria-label','Campo de composição conta B');await settle();resolveImport({ok:true,value:{conversationId:id,runIds:[id]}});await flush();
 assert.equal(shadow.querySelector('section'),null);assert.equal(s.calls.filter(r=>r.type==='mab:progress').length,0);assert.ok(s.host('c'),'ações são religadas ao contexto atual sem chamada ao modelo');s.close();
});
test('IDs reutilizados pelo virtualizador não mantêm ação ligada ao alvo anterior',async()=>{
 const s=setup(),oldHost=s.host('c');open(s,'c');s.document.querySelector('[data-id="c"]').setAttribute('data-id','remounted');await settle();assert.equal(oldHost.isConnected,false);assert.ok(s.host('remounted'));assert.equal(s.host('remounted').shadowRoot.querySelector('section'),null);s.close();
});
test('controles e sugestões não contaminam a extração subsequente',()=>{
 const s=setup();open(s,'c');const row=s.document.querySelector('[data-id="c"]'),fake=s.document.createElement('div');fake.setAttribute('data-mab-ui','fixture');fake.innerHTML='<div data-id="injected"><div aria-label="Conversa fictícia:"></div><span class="selectable-text">NÃO CAPTURAR CONTROLE MAB</span></div>';row.append(fake);
 const captured=s.context.MabWhatsAppCapture.captureWhatsApp();assert.ok(!JSON.stringify(captured).includes('NÃO CAPTURAR'));assert.equal(captured.messages.find(m=>m.sourceId==='c').text,'Aceitam Pix?');s.close();
});

test('fechar e reabrir preserva sugestão e importação sem nova execução paga',async()=>{
 const s=setup(),first=open(s,'c');select(first,'architecture','centralized_orchestration');select(first,'context','target');select(first,'runtime','real');click(s,first.getElementById('generate'));await flush();await flush();
 const firstRequest=s.calls.find(r=>r.type==='mab:import');click(s,first.getElementById('close'));const reopened=open(s,'c');assert.equal(reopened.getElementById('response').textContent,'Aceitamos Pix no contexto controlado.');
 click(s,reopened.getElementById('generate'));await flush();await flush();assert.equal(s.calls.filter(r=>r.type==='mab:import').length,1);assert.equal(firstRequest.capture.captureId,s.calls.find(r=>r.type==='mab:import').capture.captureId);s.close();
});
test('falha ao preparar captura é explicada abaixo da ação, sem chamada à API',()=>{
 const s=setup();s.context.MabWhatsAppCapture.captureWhatsApp=()=>{throw new Error('O trecho carregado tem mais de 200 mensagens.');};const shadow=open(s,'c');assert.match(shadow.querySelector('[role=alert]').textContent,/200 mensagens/);assert.equal(s.calls.length,0);s.close();
});

test('editores são nativos no light DOM e projetados em slots, sem retargeting para o host',()=>{
 const s=setup(),shadow=open(s,'c'),target=field(shadow,'target');
 assert.equal(target.getRootNode(),s.document);assert.equal(target.parentElement,s.host('c'));assert.equal(target.tagName,'TEXTAREA');assert.equal(target.getAttribute('slot'),'mab-target');assert.ok(shadow.querySelector('slot[name="mab-target"]'));
 for(const name of ['architecture','context','runtime'])assert.equal(field(shadow,name).getRootNode(),s.document);
 s.close();
});
test('teclado, composição, foco e clipboard dos controles não propagam nem bloqueiam edição padrão',()=>{
 const s=setup(),shadow=open(s,'c'),target=field(shadow,'target'),composer=s.document.querySelector('footer [contenteditable]');composer.textContent='Rascunho original preservado';
 let leaked=0;const names=['pointerdown','mousedown','click','focusin','keydown','keypress','keyup','beforeinput','input','compositionstart','compositionend','paste','copy','cut'];
 for(const name of names){s.document.addEventListener(name,()=>leaked++);const event=new s.window.Event(name,{bubbles:true,cancelable:true,composed:true});target.dispatchEvent(event);assert.equal(event.defaultPrevented,false,`${name}: manter comportamento nativo`);}
 assert.equal(leaked,0);assert.equal(composer.textContent,'Rascunho original preservado');assert.equal(s.calls.length,0);s.close();
});
test('fechar e reabrir remove e restaura os mesmos controles sem duplicação nem perda do texto',()=>{
 const s=setup(),shadow=open(s,'c'),original=field(shadow,'target');original.value='Texto editado preservado';click(s,shadow.getElementById('close'));assert.equal(s.host('c').querySelectorAll('[data-mab-control]').length,0);
 const reopened=open(s,'c');assert.equal(field(reopened,'target'),original);assert.equal(original.value,'Texto editado preservado');assert.equal(original.getRootNode(),s.document);assert.equal(s.host('c').querySelectorAll('[data-mab-control]').length,4);s.close();
});

test('reativar remove somente hosts antigos da extensão antes de montar ações novas',()=>{
 const s=setup();s.close();const stale=s.document.createElement('div');stale.setAttribute('data-mab-ui','message-action');s.document.querySelector('[data-id="c"]').append(stale);
 const unrelated=s.document.createElement('div');unrelated.setAttribute('data-mab-ui','unrelated');s.document.getElementById('main').append(unrelated);
 s.context.MabWhatsAppMessages.toggle();assert.equal(stale.isConnected,false);assert.equal(unrelated.isConnected,true);assert.equal(s.document.querySelectorAll('[data-mab-ui="message-action"]').length,3);s.close();
});

const markerIds=s=>Array.from(s.document.querySelectorAll('[data-mab-ui="context-marker"]'),node=>node.getAttribute('data-mab-source')).sort();
test('marcadores correspondem exatamente ao prefixo enviado, distinguem alvo e contexto e excluem futuro',async()=>{
 const s=setup(),shadow=open(s,'c');assert.deepEqual(markerIds(s),['a','b','c']);
 assert.equal(s.document.querySelector('[data-mab-source="c"]').getAttribute('data-mab-context'),'target');
 assert.equal(s.document.querySelector('[data-mab-source="b"]').getAttribute('data-mab-context'),'context');
 select(shadow,'architecture','centralized_orchestration');select(shadow,'context','recent');select(shadow,'runtime','real');click(s,shadow.getElementById('generate'));await flush();await flush();
 const request=s.calls.find(r=>r.type==='mab:import');assert.deepEqual(markerIds(s),Array.from(request.capture.messages,m=>m.sourceId).sort());assert.equal(s.document.querySelector('[data-mab-source="d"]'),null);s.close();
});
test('trocar contexto ou solicitação atualiza marcadores imediatamente sem enviar dados',()=>{
 const s=setup(),shadow=open(s,'c');select(shadow,'context','target');assert.deepEqual(markerIds(s),['c']);select(shadow,'context','recent');assert.deepEqual(markerIds(s),['a','b','c']);
 open(s,'a');assert.deepEqual(markerIds(s),['a']);assert.equal(s.calls.length,0);s.close();assert.deepEqual(markerIds(s),[]);
});
test('texto ajustado aparece no marcador do alvo e no preview exato sem alterar bolha original',()=>{
 const s=setup(),shadow=open(s,'c'),target=field(shadow,'target');target.value='Solicitação ajustada para o teste';target.dispatchEvent(new s.window.Event('input',{bubbles:true}));
 const marker=s.document.querySelector('[data-mab-source="c"]');assert.match(marker.shadowRoot.querySelector('span').textContent,/Texto ajustado no MAB/);assert.match(shadow.getElementById('marker-legend').textContent,/texto ajustado/);
 assert.match(shadow.getElementById('preview').textContent,/Solicitação ajustada para o teste/);assert.equal(s.document.querySelector('[data-id="c"] .selectable-text').textContent,'Aceitam Pix?');
 assert.equal(s.context.MabWhatsAppCapture.captureWhatsApp().messages.find(m=>m.sourceId==='c').text,'Aceitam Pix?');
 click(s,shadow.getElementById('close'));assert.deepEqual(markerIds(s),[]);s.close();
});
test('troca de conversa e reciclagem de ID retiram marcadores da execução anterior',async()=>{
 const s=setup();open(s,'c');assert.deepEqual(markerIds(s),['a','b','c']);s.document.querySelector('[data-id="c"]').setAttribute('data-id','recycled');await settle();assert.deepEqual(markerIds(s),[]);
 open(s,'recycled');assert.ok(markerIds(s).length);s.document.querySelector('footer [contenteditable]').setAttribute('aria-label','Outra conta da conversa');await settle();assert.deepEqual(markerIds(s),[]);s.close();
});

test('inserção exige clique real, usa a resposta concluída da aba e revalida a conversa',async()=>{
 const s=setup(),shadow=open(s,'c'),inserted=[];
 s.context.MabWhatsAppComposer={insertReply:args=>{assert.equal(args.main,s.document.getElementById('main'));assert.equal(args.isCurrent(),true);inserted.push(args.text);return{appended:true};}};
 s.context.chrome.runtime.sendMessage=async request=>{s.calls.push(request);return{ok:true,value:request.type==='mab:import'?{conversationId:id,runIds:[id]}:{runs:[{id,name:'Centralizada',text:'Sugestão centralizada',finished:true},{id:'workflow',name:'Workflow',text:'Sugestão workflow\nSegunda linha',finished:true}],finished:true,ready:2}};};
 assert.equal(shadow.getElementById('insert').disabled,true);
 click(s,shadow.getElementById('generate'));await flush();await flush();
 const insert=shadow.getElementById('insert');assert.equal(insert.disabled,false);
 click(s,shadow.querySelectorAll('[role=tab]')[1]);click(s,insert,false);assert.deepEqual(inserted,[]);
 click(s,insert);assert.deepEqual(inserted,['Sugestão workflow\nSegunda linha']);assert.match(shadow.getElementById('status').textContent,/acrescentada ao rascunho/);assert.deepEqual(s.copied,[]);
 s.document.querySelector('footer [contenteditable]').setAttribute('aria-label','Campo de outra conversa');click(s,insert);assert.equal(inserted.length,1);s.close();
});
test('resposta pendente ou com erro não pode ser inserida, e falha de inserção fica visível',async()=>{
 const s=setup(),shadow=open(s,'c');let attempts=0;
 s.context.MabWhatsAppComposer={insertReply:()=>{attempts++;throw new Error('Confira o rascunho e use Copiar resposta.');}};
 s.context.chrome.runtime.sendMessage=async request=>({ok:true,value:request.type==='mab:import'?{conversationId:id,runIds:[id]}:{runs:[{id,name:'Pendente',text:'Parcial',finished:false},{id:'failed',name:'Falhou',text:'Parcial com falha',finished:true,error:'Falha do modelo'},{id:'ready',name:'Pronta',text:'Resposta completa',finished:true}],finished:true,ready:1}});
 click(s,shadow.getElementById('generate'));await flush();await flush();
 assert.equal(shadow.getElementById('insert').disabled,true);click(s,shadow.getElementById('insert'));assert.equal(attempts,0);
 click(s,shadow.querySelectorAll('[role=tab]')[1]);assert.equal(shadow.getElementById('insert').disabled,true);click(s,shadow.getElementById('insert'));assert.equal(attempts,0);
 click(s,shadow.querySelectorAll('[role=tab]')[2]);assert.equal(shadow.getElementById('insert').disabled,false);click(s,shadow.getElementById('insert'));assert.equal(attempts,1);assert.match(shadow.getElementById('status').textContent,/Confira o rascunho/);s.close();
});

function pollingClock(){
 const queue=[];return{queue,setTimeout(fn,delay){if(delay===1800){const timer={fn,cancelled:false};queue.push(timer);return timer;}return setTimeout(fn,delay);},clearTimeout(timer){if(timer&&typeof timer==='object'&&'cancelled'in timer)timer.cancelled=true;else clearTimeout(timer);},step(){let timer;do{timer=queue.shift();}while(timer?.cancelled);if(timer)timer.fn();}};
}
const progressRun=(id,architecture,status,text='')=>({id,architecture,name:({centralized_orchestration:'Centralizada',structured_workflow:'Workflow',decentralized_swarm:'Swarm'})[architecture],status,text,finished:['completed','failed','cancelled','human_review_required'].includes(status),...(status==='failed'?{error:'Falha do modelo'}:{}),...(status==='human_review_required'?{reviewRequired:true}:{})});

test('progresso é imediato no envio, mostra estados reais por arquitetura e encerra sem mascarar falha',async()=>{
 const timer=pollingClock(),s=setup(timer),shadow=open(s,'c');select(shadow,'architecture','all_architectures');let accept;
 let snapshot={runs:[progressRun(id,'centralized_orchestration','completed','Resposta pronta'),progressRun('w','structured_workflow','pending'),progressRun('s','decentralized_swarm','running')],finished:false,ready:1};
 s.context.chrome.runtime.sendMessage=request=>{s.calls.push(request);if(request.type==='mab:import')return new Promise(resolve=>{accept=resolve;});return Promise.resolve({ok:true,value:snapshot});};
 click(s,shadow.getElementById('generate'));
 assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'sending');assert.equal(shadow.getElementById('progress-title').textContent,'Enviando trecho');assert.equal(shadow.getElementById('generate').getAttribute('aria-busy'),'true');assert.equal(shadow.querySelector('section').hasAttribute('aria-busy'),false);assert.equal(shadow.getElementById('progress-runs').children.length,3);
 accept({ok:true,value:{conversationId:id,runIds:[id,'w','s']}});await flush();await flush();
 assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'running');assert.match(shadow.getElementById('progress-summary').textContent,/1 de 3 finalizadas/);assert.match(shadow.getElementById('progress-runs').textContent,/Na fila/);assert.match(shadow.getElementById('progress-runs').textContent,/Em execução/);assert.equal(shadow.getElementById('insert').disabled,false);
 const stable=shadow.getElementById('progress-runs').firstChild;timer.step();await flush();await flush();assert.equal(shadow.getElementById('progress-runs').firstChild,stable,'snapshot repetido não recria anúncios live');
 snapshot={runs:[progressRun(id,'centralized_orchestration','completed','Resposta pronta'),progressRun('w','structured_workflow','failed'),progressRun('s','decentralized_swarm','cancelled')],finished:true,ready:1};timer.step();await flush();await flush();
 assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'complete');assert.equal(shadow.getElementById('progress-title').textContent,'Processamento encerrado');assert.match(shadow.getElementById('progress-summary').textContent,/3 de 3 finalizadas.*1 falha.*1 cancelada/);assert.match(shadow.getElementById('progress-runs').textContent,/Falhou/);assert.match(shadow.getElementById('progress-runs').textContent,/Cancelada/);assert.equal(shadow.getElementById('generate').getAttribute('aria-busy'),'false');s.close();
});

test('erro de consulta mantém último estado, trocar aba não reinicia progresso e retry não reimporta',async()=>{
 const timer=pollingClock(),s=setup(timer),shadow=open(s,'c');select(shadow,'architecture','all_architectures');let fail=false,complete=false;
 s.context.chrome.runtime.sendMessage=async request=>{s.calls.push(request);if(request.type==='mab:import')return{ok:true,value:{conversationId:id,runIds:[id,'w']}};if(fail)return{ok:false,error:'Conexão de teste indisponível'};return{ok:true,value:{runs:[progressRun(id,'centralized_orchestration','completed','Resposta'),progressRun('w','structured_workflow',complete?'completed':'running',complete?'Outra resposta':'')],finished:complete,ready:complete?2:1}};};
 click(s,shadow.getElementById('generate'));await flush();await flush();fail=true;timer.step();await flush();await flush();assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'error');assert.equal(shadow.getElementById('generate').getAttribute('aria-busy'),'false');assert.match(shadow.getElementById('progress-summary').textContent,/Último estado recebido/);
 click(s,shadow.querySelectorAll('[role=tab]')[1]);assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'error');fail=false;complete=true;click(s,shadow.getElementById('generate'));await flush();await flush();assert.equal(s.calls.filter(request=>request.type==='mab:import').length,1);assert.equal(shadow.getElementById('progress-title').textContent,'Respostas disponíveis');
 click(s,shadow.getElementById('new'));assert.equal(shadow.getElementById('progress').hidden,true);assert.equal(shadow.getElementById('progress-runs').children.length,0);assert.equal(shadow.getElementById('generate').getAttribute('aria-busy'),'false');s.close();
});

test('timeout pausa indicador, reabertura retoma sem import e revisão sem texto não vira resposta pronta',async()=>{
 let now=0;class ClockDate extends Date{static now(){return now;}}const timer=pollingClock(),s=setup({...timer,Date:ClockDate}),shadow=open(s,'c');let complete=false;
 s.context.chrome.runtime.sendMessage=async request=>{s.calls.push(request);return{ok:true,value:request.type==='mab:import'?{conversationId:id,runIds:[id]}:{runs:[progressRun(id,'centralized_orchestration',complete?'human_review_required':'running')],finished:complete,ready:0}};};
 click(s,shadow.getElementById('generate'));await flush();await flush();now=180001;timer.step();await flush();await flush();assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'paused');assert.equal(shadow.getElementById('generate').getAttribute('aria-busy'),'false');
 click(s,shadow.querySelector('[role=tab]'));assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'paused');click(s,shadow.getElementById('close'));complete=true;const reopened=open(s,'c');await flush();await flush();assert.equal(s.calls.filter(request=>request.type==='mab:import').length,1);assert.equal(reopened.getElementById('progress').getAttribute('data-phase'),'complete');assert.equal(reopened.getElementById('progress-title').textContent,'Processamento encerrado');assert.match(reopened.getElementById('progress-runs').textContent,/Revisão profissional · sem resposta/);assert.match(reopened.getElementById('progress-summary').textContent,/0 respostas disponíveis.*1 sem resposta/);assert.match(reopened.getElementById('metrics').textContent,/sem resposta/);assert.equal(reopened.getElementById('insert').disabled,true);s.close();
});

test('erro antes do primeiro estado não inventa execução e fechamento pausa envio sem resposta tardia',async()=>{
 const s=setup(),shadow=open(s,'c');s.context.chrome.runtime.sendMessage=async request=>{s.calls.push(request);return{ok:false,error:'API indisponível'};};click(s,shadow.getElementById('generate'));await flush();assert.equal(shadow.getElementById('progress').getAttribute('data-phase'),'error');assert.match(shadow.getElementById('progress-summary').textContent,/Sem confirmação de execução/);assert.ok(!shadow.getElementById('progress-summary').textContent.includes('Último estado recebido'));
 let release;s.context.chrome.runtime.sendMessage=request=>{s.calls.push(request);return new Promise(resolve=>{release=resolve;});};click(s,shadow.getElementById('generate'));await flush();click(s,shadow.getElementById('close'));release({ok:true,value:{conversationId:id,runIds:[id]}});await flush();assert.equal(shadow.querySelector('section'),null);assert.equal(s.calls.filter(request=>request.type==='mab:progress').length,0);const reopened=open(s,'c');assert.equal(reopened.getElementById('progress').getAttribute('data-phase'),'paused');assert.equal(reopened.getElementById('generate').getAttribute('aria-busy'),'false');s.close();
});
