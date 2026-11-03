import test from 'node:test';
import assert from 'node:assert/strict';
import '../panel-core.js';
const core = globalThis.MabPanelCore;
const capture = { captureId: 'fdf70ad9-1f78-4a96-903c-d2312383fd67', messages: Array.from({length:15}, (_, i) => ({sourceId:String(i),role:i%2?'attendant':'customer',text:`Mensagem ${i}`})) };
test('contexto recente limita dez mensagens e corta respostas futuras', () => {
 const selected=core.selectContext(capture,'12','recent');
 assert.equal(selected.messages.length,10); assert.equal(selected.messages[0].sourceId,'3'); assert.equal(selected.messages.at(-1).sourceId,'12');
 assert.equal(core.latestCustomer(capture).sourceId,'14');
});
test('somente a solicitação aceita ajuste textual sem mudar fonte nem original', () => {
 const selected=core.selectContext(capture,'12','target','Pergunta sintética revisada');
 assert.equal(selected.messages.length,1); assert.equal(selected.messages[0].text,'Pergunta sintética revisada');
 assert.equal(capture.messages[12].text,'Mensagem 12'); assert.equal(selected.messages[0].sourceId,'12');
 assert.throws(()=>core.selectContext(capture,'11','recent'),/recebida do cliente/);
});
test('resultados incluem somente os runs solicitados e excluem atendente importado', () => {
 const result=core.summarizeRuns({runs:[{id:'a',status:'completed',experiment:{architectureKey:'centralized_orchestration'}},{id:'later',status:'completed'}],messages:[
 {direction:'outbound',contentText:'resposta humana antiga',metadata:{importedHistory:true,runtimeRunId:'a'}},
 {direction:'outbound',contentText:'sugestão desta execução',metadata:{runtimeRunId:'a'}},
 {direction:'outbound',contentText:'execução posterior',metadata:{runtimeRunId:'later'}}]},['a']);
 assert.equal(result.runs.length,1); assert.equal(result.runs[0].text,'sugestão desta execução'); assert.equal(result.finished,true);
});
test('compara três arquiteturas e mantém pendência até todas terminarem', () => {
 const result=core.summarizeRuns({runs:[{id:'a',status:'completed',experiment:{architectureKey:'centralized_orchestration'}},{id:'b',status:'running',experiment:{architectureKey:'structured_workflow'}},{id:'c',status:'failed',experiment:{architectureKey:'decentralized_swarm'},summary:{stopReason:'Modelo indisponível'}}],messages:[]},['a','b','c']);
 assert.equal(result.finished,false); assert.equal(result.runs[2].error,'Modelo indisponível'); assert.equal(result.runs[2].text,'');
 assert.deepEqual(result.runs.map(r=>r.name),['Centralizada','Workflow','Swarm']);
});
test('revisão humana, cancelamento e run ausente têm estados explícitos', () => {
 const result=core.summarizeRuns({runs:[{id:'a',status:'human_review_required'},{id:'b',status:'cancelled'}],messages:[]},['a','b','missing']);
 assert.equal(result.runs[0].reviewRequired,true); assert.equal(result.runs[1].finished,true); assert.equal(result.runs[2].status,'pending'); assert.equal(result.finished,false);
});
