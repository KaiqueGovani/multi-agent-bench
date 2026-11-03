import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';
const source=fs.readFileSync(new URL('../composer.js',import.meta.url),'utf8');
function setup({draft='',extra='',hidden=false,readOnly=false,command=true,onFocus,onInput}={}){
 const {window,document}=parseHTML(`<html><body><div id="main"><footer><div id="editor" contenteditable="true" role="textbox"></div>${extra}</footer></div><button id="send">Enviar</button></body></html>`);
 const main=document.getElementById('main'),editor=document.getElementById('editor');let rendered=draft,raw=draft,active=document.body,current=true,writes=0,sends=0;
 Object.defineProperty(editor,'innerText',{get:()=>rendered});Object.defineProperty(editor,'textContent',{get:()=>raw,set:()=>{writes++;}});
 Object.defineProperty(editor,'innerHTML',{get:()=>'',set:()=>{writes++;}});Object.defineProperty(document,'activeElement',{get:()=>active});
 window.getComputedStyle=()=>({display:'block',visibility:'visible',opacity:'1'});editor.getClientRects=()=>hidden?[]:[{width:300,height:30}];
 if(readOnly)editor.setAttribute('aria-readonly','true');for(const other of document.querySelectorAll('[contenteditable]'))if(other!==editor)other.getClientRects=()=>[{width:300,height:30}];
 editor.focus=()=>{active=editor;onFocus?.({setCurrent:value=>{current=value;},editor,document});};
 const selection={anchorNode:null,range:null,removeAllRanges(){this.range=null;this.anchorNode=null;},addRange(range){this.range=range;this.anchorNode=range.editor;}};
 document.getSelection=()=>selection;document.createRange=()=>({editor:null,collapsed:false,selectNodeContents(node){this.editor=node;},collapse(){this.collapsed=true;}});
 const calls=[],keys=[];document.getElementById('send').addEventListener('click',()=>sends++);for(const name of ['keydown','keypress','keyup'])document.addEventListener(name,event=>keys.push(event));
 document.execCommand=(name,show,value)=>{calls.push({name,show,value,collapsed:selection.range?.collapsed});if(!command)return false;const insertion=name==='insertLineBreak'?'\n':value;if(!selection.range?.collapsed){rendered='';raw='';}rendered+=insertion;raw+=insertion;selection.range.collapsed=true;editor.dispatchEvent(new window.Event('input',{bubbles:true}));onInput?.({setCurrent:value=>{current=value;},editor,document});return true;};
 const context=vm.createContext({});vm.runInContext(source,context);
 return{window,document,main,editor,selection,calls,keys,insert:(text,guard=()=>current)=>context.MabWhatsAppComposer.insertReply({main,isCurrent:guard,text}),get draft(){return rendered;},get writes(){return writes;},get sends(){return sends;},setRaw:value=>{raw=value;},setRendered:value=>{rendered=value;},setActive:value=>{active=value;},setCurrent:value=>{current=value;}};
}
test('acrescenta ao fim do rascunho e preserva linhas sem enviar ou reescrever o DOM',()=>{
 const s=setup({draft:'Rascunho do atendente'});assert.equal(s.insert('Linha um\nLinha dois').appended,true);assert.equal(s.draft,'Rascunho do atendente\n\nLinha um\nLinha dois');assert.equal(s.calls[0].collapsed,true);assert.equal(s.writes,0);assert.equal(s.sends,0);assert.equal(s.keys.length,0);
 assert.ok(s.calls.every(call=>['insertText','insertLineBreak'].includes(call.name)));assert.ok(s.calls.filter(call=>call.name==='insertText').every(call=>call.value&&!call.value.includes('\n')));
});
test('campo vazio insere apenas a resposta usando seleção do placeholder vazio',()=>{
 const s=setup();assert.equal(s.insert('Resposta pronta').appended,false);assert.equal(s.draft,'Resposta pronta');assert.equal(s.calls[0].collapsed,false);assert.equal(s.writes,0);assert.equal(s.sends,0);
});
test('rascunho de espaços continua preservado e recebe separador',()=>{
 const s=setup({draft:'   '});assert.equal(s.insert('Resposta').appended,true);assert.equal(s.draft,'   \n\nResposta');assert.equal(s.calls[0].collapsed,true);
});
test('rascunho somente emoji/imagem é preservado e recusa edição impossível de conferir',()=>{
 const s=setup(),image=s.document.createElement('img');image.setAttribute('alt','🙂');s.editor.append(image);assert.throws(()=>s.insert('Resposta'),/conteúdo não textual/);assert.equal(s.calls.length,0);assert.equal(s.editor.querySelector('img'),image);assert.equal(s.writes,0);
});
test('recusa conversa antiga antes de focar e após troca reentrante no foco',()=>{
 let focused=0;const before=setup({onFocus:()=>focused++});before.setCurrent(false);assert.throws(()=>before.insert('Resposta'),/conversa mudou/);assert.equal(focused,0);assert.equal(before.calls.length,0);
 const after=setup({draft:'Preservar',onFocus:({setCurrent})=>setCurrent(false)});assert.throws(()=>after.insert('Resposta'),/conversa mudou/);assert.equal(after.draft,'Preservar');assert.equal(after.calls.length,0);
});
test('troca de conversa durante input interrompe linhas seguintes sem segunda tentativa',()=>{
 const s=setup({onInput:({setCurrent})=>setCurrent(false)});assert.throws(()=>s.insert('Primeira\nSegunda'),/conversa mudou/);assert.equal(s.calls.length,1);assert.equal(s.draft,'Primeira');assert.equal(s.sends,0);
});
test('recusa editor oculto, readonly, ambíguo ou removido e ignora campo da própria extensão',()=>{
 for(const options of [{hidden:true},{readOnly:true},{extra:'<div contenteditable="true" role="textbox"></div>'}]){const s=setup(options);assert.throws(()=>s.insert('Resposta'),/único campo/);assert.equal(s.calls.length,0);}
 const owned=setup({extra:'<div data-mab-ui="test"><div contenteditable="true" role="textbox"></div></div>'});assert.equal(owned.insert('Resposta').appended,false);
 const stale=setup();stale.main.remove();assert.throws(()=>stale.insert('Resposta'),/conversa mudou/);assert.equal(stale.calls.length,0);
});
test('falha nativa não tenta fallback de textContent, innerHTML ou eventos de envio',()=>{
 const s=setup({draft:'Rascunho intacto',command:false});assert.throws(()=>s.insert('Resposta'),/inserção não foi concluída/);assert.equal(s.draft,'Rascunho intacto');assert.equal(s.writes,0);assert.equal(s.sends,0);assert.equal(s.keys.length,0);
});
test('perda de foco e ausência de seleção impedem edição fora do campo validado',()=>{
 let s;s=setup({onFocus:()=>s.setActive(s.document.body)});assert.throws(()=>s.insert('Resposta'),/perdeu o foco/);assert.equal(s.calls.length,0);
 const noSelection=setup();noSelection.document.getSelection=()=>null;assert.throws(()=>noSelection.insert('Resposta'),/posicionar o cursor/);assert.equal(noSelection.calls.length,0);
});
test('texto HTML é tratado como texto e respostas vazias não acionam o editor',()=>{
 const s=setup();assert.throws(()=>s.insert('   '),/Não há uma resposta/);assert.equal(s.calls.length,0);s.insert('<b>Texto literal</b>');assert.equal(s.draft,'<b>Texto literal</b>');assert.equal(s.calls[0].name,'insertText');assert.equal(s.writes,0);
});
test('preserva LF final e linhas em branco consecutivas sem chamar insertText vazio',()=>{
 const s=setup();s.insert('Primeira\n\nÚltima\n');assert.equal(s.draft,'Primeira\n\nÚltima\n');assert.equal(s.calls.filter(call=>call.name==='insertLineBreak').length,3);assert.ok(s.calls.filter(call=>call.name==='insertText').every(call=>call.value.length));
});
