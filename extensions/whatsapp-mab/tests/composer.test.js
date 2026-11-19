import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parseHTML} from 'linkedom';

const readSource = file => fs.readFileSync(new URL(`../${file}`, import.meta.url), 'utf8');
const descriptor = (object, name) => {
  for (let proto = object; proto; proto = Object.getPrototypeOf(proto)) {
    const found = Object.getOwnPropertyDescriptor(proto, name);
    if (found) return found;
  }
};

// The editable fixture owns its DOM, as a controlled browser editor does. Native
// insertion/paste is modelled with actual paragraph/BR nodes, not rendered += LF.
function setup({draft='', html, extra='', hidden=false, readOnly=false, command=true,
  pasteSupport=true, paste, onFocus, onInput, innerTextStyle='lines', nbsp=false,
  sentinel=false}={}) {
  const {window, document}=parseHTML(`<html><body><div id="main"><footer><div id="editor" contenteditable="true" role="textbox"></div>${extra}</footer></div><button id="send">Enviar</button></body></html>`);
  const main=document.getElementById('main'), editor=document.getElementById('editor');
  let active=document.body, current=true, writes=0, sends=0;
  const calls=[], pastes=[], keys=[];
  const textDescriptor=descriptor(editor, 'textContent'), htmlDescriptor=descriptor(editor, 'innerHTML');
  const plain=node => {
    if (node.nodeType===3) return node.nodeValue;
    if (node.nodeName==='BR') return '\n';
    const children=[...node.childNodes];
    if (children.length===1 && children[0].nodeName==='BR') return '';
    return children.map((child, index) => `${index && ['P','DIV','LI'].includes(child.nodeName) ? '\n' : ''}${plain(child)}`).join('');
  };
  const render=text => {
    const children=text.split('\n').map(line => {
      const paragraph=document.createElement('p');
      if (line) paragraph.append(document.createTextNode(nbsp ? line.replaceAll(' ', '\u00a0') : line));
      else paragraph.append(document.createElement('br'));
      return paragraph;
    });
    if (sentinel && text.length) children.at(-1).append(document.createElement('br'));
    editor.replaceChildren(...children);
  };
  if (html) htmlDescriptor.set.call(editor, html); else render(draft);
  Object.defineProperty(editor, 'innerText', {get:() => {
    const value=plain(editor);
    return innerTextStyle==='flat' ? textDescriptor.get.call(editor) : innerTextStyle==='paragraph-spacing' ? value.replaceAll('\n', '\n\n') : value;
  }});
  Object.defineProperty(editor, 'textContent', {get:() => textDescriptor.get.call(editor), set:() => {writes++;}});
  Object.defineProperty(editor, 'innerHTML', {get:() => htmlDescriptor.get.call(editor), set:() => {writes++;}});
  Object.defineProperty(document, 'activeElement', {get:() => active});
  const inheritedStyle=(node, property, fallback) => {
    for (let element=node; element; element=element.parentElement) if (element.style?.[property]) return element.style[property];
    return fallback;
  };
  window.getComputedStyle=node => ({display:'block', visibility:'visible', opacity:'1',
    fontWeight:inheritedStyle(node, 'fontWeight', '400'), fontStyle:inheritedStyle(node, 'fontStyle', 'normal'),
    textDecorationLine:inheritedStyle(node, 'textDecorationLine', 'none'), fontFamily:inheritedStyle(node, 'fontFamily', 'system-ui')});
  editor.getClientRects=() => hidden ? [] : [{width:300, height:30}];
  if (readOnly) editor.setAttribute('aria-readonly', 'true');
  for (const other of document.querySelectorAll('[contenteditable]')) if (other!==editor) other.getClientRects=() => [{width:300, height:30}];
  const controls={editor, document, render, renderHTML:value => htmlDescriptor.set.call(editor, value),
    setCurrent:value => {current=value;}, setActive:value => {active=value;}};
  editor.focus=() => {active=editor; onFocus?.(controls);};
  const selection={anchorNode:null, range:null,
    removeAllRanges() {this.range=null; this.anchorNode=null;},
    addRange(range) {this.range=range; this.anchorNode=range.editor;}};
  document.getSelection=() => selection;
  document.createRange=() => ({editor:null, collapsed:false,
    selectNodeContents(node) {this.editor=node;}, collapse() {this.collapsed=true;}});
  const nativeInsert=text => {
    render((selection.range?.collapsed ? plain(editor) : '')+text);
    selection.range.collapsed=true;
    editor.dispatchEvent(new window.Event('input', {bubbles:true}));
  };
  document.execCommand=(name, show, value) => {
    calls.push({name, show, value, collapsed:selection.range?.collapsed});
    if (!command) return false;
    assert.equal(name, 'insertText', 'multiline edits must be one native insertion, never Enter/insertLineBreak');
    nativeInsert(value);
    return command!=='false-after-insert';
  };
  class DataTransfer {
    constructor() {this.data=new Map();}
    setData(type, value) {this.data.set(type, String(value));}
    getData(type) {return this.data.get(type) || '';}
    get types() {return [...this.data.keys()];}
  }
  class ClipboardEvent extends window.Event {
    constructor(type, options) {super(type, options); this.clipboardData=options.clipboardData;}
  }
  if (pasteSupport) {window.DataTransfer=DataTransfer; window.ClipboardEvent=ClipboardEvent;}
  else {window.DataTransfer=undefined; window.ClipboardEvent=undefined;}
  editor.addEventListener('paste', event => {
    pastes.push({text:event.clipboardData.getData('text/plain'), types:[...event.clipboardData.types]});
    if (paste==='consume') {event.preventDefault(); nativeInsert(event.clipboardData.getData('text/plain'));}
    else if (typeof paste==='function') paste({...controls, event, insert:nativeInsert});
  });
  editor.addEventListener('input', () => onInput?.(controls));
  document.getElementById('send').addEventListener('click', () => sends++);
  for (const name of ['keydown','keypress','keyup']) document.addEventListener(name, event => keys.push(event));
  const context=vm.createContext({setTimeout, clearTimeout, queueMicrotask, Promise,
    ...(pasteSupport ? {DataTransfer, ClipboardEvent} : {})});
  for (const file of ['formatter.js', 'composer.js']) vm.runInContext(readSource(file), context);
  return {...controls, window, main, selection, calls, pastes, keys,
    insert:(text, guard=() => current) => context.MabWhatsAppComposer.insertReply({main, isCurrent:guard, text}),
    get draft() {return plain(editor);}, get writes() {return writes;}, get sends() {return sends;}};
}

const noSend = s => {assert.equal(s.writes, 0); assert.equal(s.sends, 0); assert.equal(s.keys.length, 0);};
const insertionFailure = /inserção|inserir|rascunho|conferir|confirmar/i;

test('cola texto completo com markup WhatsApp e parágrafos pelo handler do editor', async () => {
  const s=setup({paste:'consume'});
  assert.equal((await s.insert('## Disponibilidade\n\n**Paracetamol**: 23 caixas\nPreço não informado.')).appended, false);
  assert.equal(s.draft, '*Disponibilidade*\n\n*Paracetamol*: 23 caixas\nPreço não informado.');
  assert.equal(s.pastes.length, 1);
  assert.deepEqual(s.pastes[0].types, ['text/plain']);
  assert.equal(s.calls.length, 0, 'a colagem consumida não recebe uma segunda inserção');
  noSend(s);
});

test('preserva o rascunho e acrescenta a resposta com uma linha em branco', async () => {
  const s=setup({draft:'Rascunho do atendente', paste:'consume'});
  assert.equal((await s.insert('Linha um\nLinha dois')).appended, true);
  assert.equal(s.draft, 'Rascunho do atendente\n\nLinha um\nLinha dois');
  assert.equal(s.pastes[0].text, '\n\nLinha um\nLinha dois');
  assert.equal(s.selection.range.collapsed, true);
  noSend(s);
});

test('colagem sem handler usa uma única insertText multilinha', async () => {
  const s=setup();
  await s.insert('Primeira\n\nÚltima\n');
  assert.equal(s.draft, 'Primeira\n\nÚltima\n');
  assert.equal(s.pastes.length, 1);
  assert.equal(s.calls.length, 1);
  assert.deepEqual(s.calls[0], {name:'insertText', show:false, value:'Primeira\n\nÚltima\n', collapsed:false});
  noSend(s);
});

test('navegador sem ClipboardEvent usa a mesma inserção nativa completa', async () => {
  const s=setup({pasteSupport:false, draft:'Texto existente'});
  await s.insert('**Resposta**\nSegunda linha');
  assert.equal(s.draft, 'Texto existente\n\n*Resposta*\nSegunda linha');
  assert.equal(s.pastes.length, 0);
  assert.equal(s.calls.length, 1);
  noSend(s);
});

test('aguarda o editor reconciliar a colagem sem duplicar a resposta', async () => {
  const s=setup({paste:({event, insert}) => {
    event.preventDefault();
    setTimeout(() => insert(event.clipboardData.getData('text/plain')), 0);
  }});
  await s.insert('Linha um\nLinha dois');
  assert.equal(s.draft, 'Linha um\nLinha dois');
  assert.equal(s.pastes.length, 1);
  assert.equal(s.calls.length, 0);
  noSend(s);
});

test('verifica blocos e BR reais mesmo quando innerText não representa as linhas', async () => {
  for (const innerTextStyle of ['flat', 'paragraph-spacing']) {
    const s=setup({paste:'consume', innerTextStyle});
    await s.insert('Primeira\n\nTerceira');
    assert.equal(s.draft, 'Primeira\n\nTerceira');
    assert.equal(s.editor.querySelectorAll('p').length, 3);
    assert.equal(s.calls.length, 0);
    noSend(s);
  }
});

test('NBSP e quebra sentinela do editor não viram falha de inserção completa', async () => {
  const s=setup({paste:'consume', nbsp:true, sentinel:true});
  await s.insert('Paracetamol: 23 caixas\nPreço não informado.');
  assert.equal(s.draft.replaceAll('\u00a0', ' ').replace(/\n$/, ''), 'Paracetamol: 23 caixas\nPreço não informado.');
  assert.equal(s.calls.length, 0);
  noSend(s);
});

test('preserva os espaços do rascunho em vez de tratá-los como placeholder', async () => {
  const s=setup({draft:'   ', paste:'consume'});
  assert.equal((await s.insert('Resposta')).appended, true);
  assert.equal(s.draft, '   \n\nResposta');
  noSend(s);
});

test('placeholder p/br vazio não acrescenta linha antes da resposta', async () => {
  const s=setup({html:'<p><br></p>', paste:'consume'});
  assert.equal((await s.insert('Resposta pronta')).appended, false);
  assert.equal(s.draft, 'Resposta pronta');
  noSend(s);
});

test('rascunho somente imagem é preservado e não recebe edição insegura', async () => {
  const s=setup({html:'<img alt="🙂">'});
  const image=s.editor.querySelector('img');
  await assert.rejects(async () => s.insert('Resposta'), /conteúdo não textual/);
  assert.equal(s.calls.length, 0);
  assert.equal(s.pastes.length, 0);
  assert.equal(s.editor.querySelector('img'), image);
  noSend(s);
});

test('colagem cancelada sem conteúdo não dispara fallback nem sucesso falso', async () => {
  const s=setup({draft:'Preservado', paste:({event}) => event.preventDefault()});
  await assert.rejects(async () => s.insert('Resposta'), insertionFailure);
  assert.equal(s.draft, 'Preservado');
  assert.equal(s.calls.length, 0);
  assert.equal(s.pastes.length, 1);
  noSend(s);
});

test('colagem parcial ou que perde quebras falha e não repete o conteúdo', async () => {
  for (const transform of [text => text.slice(0, 6), text => text.replaceAll('\n', '')]) {
    const s=setup({paste:({event, insert}) => {
      event.preventDefault(); insert(transform(event.clipboardData.getData('text/plain')));
    }});
    await assert.rejects(async () => s.insert('Primeira\nSegunda'), insertionFailure);
    assert.equal(s.calls.length, 0);
    assert.equal(s.pastes.length, 1);
    noSend(s);
  }
});

test('mudança parcial sem cancelamento também bloqueia fallback duplicado', async () => {
  const s=setup({paste:({insert}) => insert('Parcial')});
  await assert.rejects(async () => s.insert('Resposta completa'), insertionFailure);
  assert.equal(s.draft, 'Parcial');
  assert.equal(s.calls.length, 0);
  noSend(s);
});

test('recusa conversa antiga antes do foco e após troca reentrante no foco', async () => {
  let focused=0;
  const before=setup({onFocus:() => focused++}); before.setCurrent(false);
  await assert.rejects(async () => before.insert('Resposta'), /conversa mudou/i);
  assert.equal(focused, 0); assert.equal(before.calls.length, 0); assert.equal(before.pastes.length, 0);
  const after=setup({draft:'Preservar', onFocus:({setCurrent}) => setCurrent(false)});
  await assert.rejects(async () => after.insert('Resposta'), /conversa mudou/i);
  assert.equal(after.draft, 'Preservar'); assert.equal(after.calls.length, 0); assert.equal(after.pastes.length, 0);
});

test('troca de conversa durante a colagem impede fallback e confirmação tardia', async () => {
  const s=setup({paste:({event, insert}) => {event.preventDefault(); insert('Primeira\nSegunda');},
    onInput:({setCurrent}) => setCurrent(false)});
  await assert.rejects(async () => s.insert('Primeira\nSegunda'), /conversa mudou/i);
  assert.equal(s.calls.length, 0); assert.equal(s.pastes.length, 1);
  noSend(s);
});

test('recusa editor oculto, readonly, ambíguo ou removido e ignora campos da extensão', async () => {
  for (const options of [{hidden:true}, {readOnly:true}, {extra:'<div contenteditable="true" role="textbox"></div>'}]) {
    const s=setup(options);
    await assert.rejects(async () => s.insert('Resposta'), /único campo/);
    assert.equal(s.calls.length, 0); assert.equal(s.pastes.length, 0);
  }
  const owned=setup({extra:'<div data-mab-ui="test"><div contenteditable="true" role="textbox"></div></div>', paste:'consume'});
  assert.equal((await owned.insert('Resposta')).appended, false);
  const stale=setup(); stale.main.remove();
  await assert.rejects(async () => stale.insert('Resposta'), /conversa mudou/i);
  assert.equal(stale.calls.length, 0); assert.equal(stale.pastes.length, 0);
});

test('falha nativa preserva o rascunho sem DOM direto nem eventos de envio', async () => {
  const s=setup({draft:'Rascunho intacto', command:false, pasteSupport:false});
  await assert.rejects(async () => s.insert('Resposta'), insertionFailure);
  assert.equal(s.draft, 'Rascunho intacto'); assert.equal(s.calls.length, 1);
  noSend(s);
});

test('perda de foco ou ausência de seleção impedem editar outro campo', async () => {
  const s=setup({onFocus:({setActive, document}) => setActive(document.body)});
  await assert.rejects(async () => s.insert('Resposta'), /perdeu o foco/);
  assert.equal(s.calls.length, 0); assert.equal(s.pastes.length, 0);
  const noSelection=setup(); noSelection.document.getSelection=() => null;
  await assert.rejects(async () => noSelection.insert('Resposta'), /posicionar o cursor/);
  assert.equal(noSelection.calls.length, 0); assert.equal(noSelection.pastes.length, 0);
});

test('perda de foco enquanto a colagem é reconciliada não aciona segunda inserção', async () => {
  const s=setup({paste:({event, setActive, document}) => {event.preventDefault(); setActive(document.body);}});
  await assert.rejects(async () => s.insert('Resposta'), /foco|campo|rascunho/);
  assert.equal(s.calls.length, 0); assert.equal(s.pastes.length, 1);
  noSend(s);
});

test('HTML é texto literal e resposta vazia nunca aciona o editor', async () => {
  const s=setup({paste:'consume'});
  await assert.rejects(async () => s.insert('   '), /Não há uma resposta/);
  assert.equal(s.calls.length, 0); assert.equal(s.pastes.length, 0);
  await s.insert('<b>Texto literal</b>');
  assert.equal(s.draft, '<b>Texto literal</b>');
  assert.equal(s.editor.querySelector('b'), null);
  noSend(s);
});

test('reconhece markup consumido somente quando o DOM mantém a formatação', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<p><strong>Disponibilidade</strong></p><p>23 caixas</p>');
  }});
  await s.insert('**Disponibilidade**\n23 caixas');
  assert.equal(s.draft, 'Disponibilidade\n23 caixas');
  assert.equal(s.editor.querySelector('strong').textContent, 'Disponibilidade');
  assert.equal(s.calls.length, 0); noSend(s);

  const lost=setup({paste:({event, insert}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain').replaceAll('*', ''));
  }});
  await assert.rejects(async () => lost.insert('**Disponibilidade**\n23 caixas'), insertionFailure);
  assert.equal(lost.calls.length, 0); noSend(lost);
});

test('formatação de rascunho anterior permanece ao acrescentar nova resposta formatada', async () => {
  const s=setup({html:'<p><strong>Rascunho do atendente</strong></p>', paste:({event, editor, document}) => {
    event.preventDefault();
    assert.equal(event.clipboardData.getData('text/plain'), '\n\n*Resposta*\nSegunda linha');
    const empty=document.createElement('p'); empty.append(document.createElement('br'));
    const answer=document.createElement('p'), strong=document.createElement('strong'); strong.append(document.createTextNode('Resposta')); answer.append(strong);
    const line=document.createElement('p'); line.append(document.createTextNode('Segunda linha'));
    editor.append(empty, answer, line);
  }});
  const original=s.editor.querySelector('strong');
  assert.equal((await s.insert('**Resposta**\nSegunda linha')).appended, true);
  assert.equal(s.draft, 'Rascunho do atendente\n\nResposta\nSegunda linha');
  assert.equal(s.editor.querySelector('strong'), original);
  assert.equal(s.editor.querySelectorAll('strong').length, 2);
  assert.equal(s.calls.length, 0); noSend(s);
});

test('emojis com ZWJ são preservados durante a conferência das linhas', async () => {
  const s=setup({paste:'consume'});
  await s.insert('Atendimento 👩‍⚕️\nPodemos ajudar.');
  assert.equal(s.draft, 'Atendimento 👩‍⚕️\nPodemos ajudar.');
  noSend(s);
});

test('resultado nativo completo prevalece sobre retorno falso legado do comando', async () => {
  const s=setup({pasteSupport:false, command:'false-after-insert'});
  await s.insert('Primeira\nSegunda');
  assert.equal(s.draft, 'Primeira\nSegunda');
  assert.equal(s.calls.length, 1); noSend(s);
});

test('reconhece negrito de spans do editor sem duplicar o estilo herdado', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<p><span style="font-weight:700"><span>Disponibilidade</span></span></p><p>23 caixas</p>');
  }});
  await s.insert('**Disponibilidade**\n23 caixas');
  assert.equal(s.draft, 'Disponibilidade\n23 caixas');
  assert.equal(s.calls.length, 0); noSend(s);
});

test('confere quebras BR entre spans e ignora apenas a sentinela final', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<span>Primeira</span><br><br><span>Terceira</span><br>');
  }});
  await s.insert('Primeira\n\nTerceira');
  assert.equal(s.draft, 'Primeira\n\nTerceira\n');
  assert.equal(s.calls.length, 0); noSend(s);
});

test('reconhece tachado de span quando o editor consome as marcas WhatsApp', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<p><span style="text-decoration-line:line-through"><span>Preço antigo</span></span></p><p>Preço não informado.</p>');
  }});
  await s.insert('~~Preço antigo~~\nPreço não informado.');
  assert.equal(s.draft, 'Preço antigo\nPreço não informado.');
  assert.equal(s.calls.length, 0); noSend(s);
});

test('reconhece código inline monoespaçado quando o editor consome as crases', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<p><span style="font-family:monospace"><span>stock_lookup</span></span></p><p>Preço não informado.</p>');
  }});
  await s.insert('`stock_lookup`\nPreço não informado.');
  assert.equal(s.draft, 'stock_lookup\nPreço não informado.');
  assert.equal(s.calls.length, 0); noSend(s);
});

test('preserva rascunhos com dois ou três parágrafos vazios ao acrescentar resposta', async () => {
  for (const count of [2, 3]) {
    const s=setup({html:'<p><br></p>'.repeat(count), paste:'consume'});
    const before='\n'.repeat(count-1);
    assert.equal(s.draft, before);
    assert.equal((await s.insert('Resposta')).appended, true);
    assert.equal(s.draft, `${before}\n\nResposta`);
    assert.equal(s.pastes[0].text, '\n\nResposta');
    assert.equal(s.calls.length, 0); noSend(s);
  }
});

test('reconhece monoespaçado quando o editor consome três crases', async () => {
  const s=setup({paste:({event, insert, renderHTML}) => {
    event.preventDefault(); insert(event.clipboardData.getData('text/plain'));
    renderHTML('<p><span style="font-family:monospace"><span>código</span></span></p>');
  }});
  await s.insert('```código```');
  assert.equal(s.draft, 'código');
  assert.equal(s.calls.length, 0); noSend(s);
});
