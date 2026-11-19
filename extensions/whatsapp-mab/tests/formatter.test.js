import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const context = vm.createContext({});
vm.runInContext(fs.readFileSync(new URL('../formatter.js', import.meta.url), 'utf8'), context);
const format = context.MabWhatsAppFormatter.toWhatsApp;

test('converts common model Markdown and keeps paragraphs, quantities and list lines', () => {
  const input = '## Disponibilidade\n\n**Produto de exemplo**: 23 caixas\n\n- Quantidade confirmada\n- ~~Preço antigo~~\n\n1. Consulte o atendimento\n2. Aguarde a confirmação\n';
  assert.equal(format(input), '*Disponibilidade*\n\n*Produto de exemplo*: 23 caixas\n\n- Quantidade confirmada\n- ~Preço antigo~\n\n1. Consulte o atendimento\n2. Aguarde a confirmação\n');
});

test('formats headings once without nested bold markers', () => {
  for (const [input, expected] of [
    ['# Título', '*Título*'], ['  ### Título ###', '  *Título*'],
    ['## **Título** e texto', '*Título e texto*'],
    ['## *Título* e texto', '*Título e texto*'],
    ['## Use `**literal**`', '*Use `**literal**`*'],
  ]) assert.equal(format(input), expected);
});

test('preserves already supported WhatsApp markup', () => {
  const text = '*Título*\n_texto em itálico_ e ~riscado~\n\n* item\n> citação\n1. primeiro\n```texto monoespaçado```';
  assert.equal(format(text), text);
});

test('turns Markdown links into readable labels and preserves the actual URL', () => {
  assert.equal(format('[Atendimento](https://example.org/atendimento)'), 'Atendimento (https://example.org/atendimento)');
  assert.equal(format('[Guia](https://example.org/a_(b)?q=1 "Título opcional")'), 'Guia (https://example.org/a_(b)?q=1)');
  assert.equal(format('[https://example.org](https://example.org)'), 'https://example.org');
  assert.equal(format('[Email](mailto:exemplo@example.org)'), 'Email (mailto:exemplo@example.org)');
  assert.equal(format('[Local](/guia) e [script](javascript:alert(1))'), '[Local](/guia) e [script](javascript:alert(1))');
});

test('keeps code contents literal instead of rewriting stars, headings or links', () => {
  const text = 'Use `**literal**` e ``[literal](https://example.org)``.\n\n```js\n## Não converter\nconst x = "**literal**";\n```\n\n~~~text\n~~literal~~\n~~~\n\n    **código indentado**\n\t[link](https://example.org)';
  assert.equal(format(text), text);
  assert.equal(format('```js\n**bloco ainda aberto**'), '```js\n**bloco ainda aberto**');
  assert.equal(format('Texto `**código sem fechamento'), 'Texto `**código sem fechamento');
});

test('HTML remains literal plain text and escaped or unmatched markers remain intact', () => {
  const text = '<img src=x onerror="alert(1)">\n<b>texto</b> &amp;\n\\**literal**\n**sem fechamento\n~~sem fechamento';
  assert.equal(format(text), text);
});

test('normalizes CRLF without collapsing blank lines or changing emoji', () => {
  assert.equal(format('Olá 👩‍⚕️\r\n\r\n**Exemplo**\r\n\r\n'), 'Olá 👩‍⚕️\n\n*Exemplo*\n\n');
  assert.equal(format('  texto  \n\n\nFim\n'), '  texto  \n\n\nFim\n');
});

test('conversion is idempotent for model Markdown, WhatsApp, literal code and links', () => {
  const examples = [
    '## **Título**\n\n**Disponível** e ~~antigo~~',
    '***destaque*** e __forte__',
    '*WhatsApp* e _itálico_\n\n~riscado~',
    '[Guia **útil**](https://example.org/a_(b))',
    '# Use `**literal**`\n```js\n**código**\n```',
    'Texto sem marcadores\n\n- linha\n',
    '**a****a**__b__', '**a**__b__**c**',
    '## [**Guia**](https://example.org/guia)',
  ];
  for (const value of examples) assert.equal(format(format(value)), format(value), value);
});
