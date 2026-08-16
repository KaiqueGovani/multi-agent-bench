# Open Questions — colaboração assíncrona

Este mecanismo permite que os agentes solicitem decisões, contexto prático ou conhecimento dos autores sem interromper o Ralph loop. Cada pergunta possui um registro versionado e uma GitHub Issue para conversa assíncrona.

## Quando abrir

Abra uma pergunta somente quando a resposta humana:

- desbloquear ou enriquecer materialmente uma seção;
- definir uma escolha metodológica ou de escopo;
- esclarecer uma experiência ou decisão dos autores que não esteja documentada;
- resolver uma divergência que não possa ser determinada pelo código, documentos ou literatura.

Não abra perguntas genéricas, duplicadas, respondíveis por pesquisa ou destinadas apenas a confirmar uma preferência editorial pequena.

## Formato obrigatório

1. Reserve o próximo identificador `OQ-NNN` em `questions.yml`.
2. Registre pergunta, contexto, capítulo afetado, prioridade, caráter bloqueante e recomendação inicial.
3. Abra uma Issue intitulada `[TCC][Open Question][OQ-NNN] pergunta curta` usando `issue-template.md`.
4. Adicione a URL e o número da Issue ao registro.
5. Mantenha no máximo cinco questões ativas e crie no máximo uma por execução.

## Como responder

O humano pode comentar livremente na Issue. Para facilitar a detecção, recomenda-se iniciar a resposta conclusiva com:

`ANSWER: decisão ou informação`

Se a resposta ainda depender de discussão, use:

`NEEDS DISCUSSION: ponto pendente`

## Ciclo de vida

- `open`: aguardando resposta humana.
- `answered`: existe uma resposta, ainda não incorporada.
- `integrated`: resposta incorporada e rastreada no manuscrito/estado.
- `closed_without_change`: encerrada sem alteração textual, com justificativa.

Ao integrar, o agente registra resumo, autor, data, arquivos/seções afetados e commit/PR. Em seguida, comenta na Issue indicando onde a resposta foi usada e encerra a Issue.

## Limites

- Respostas humanas não substituem evidências acadêmicas para afirmações factuais externas.
- Open Questions não podem abrir os evidence gates dos capítulos 7, 8 e 9.
- Nenhuma pergunta ou resposta pode conter dados pessoais, mensagens brutas de WhatsApp, credenciais ou informações de saúde identificáveis.

