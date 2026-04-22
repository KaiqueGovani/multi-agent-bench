# Plano de execucao da POC

Este plano organiza a implementacao da POC em ordem cronologica. O objetivo e construir primeiro os contratos e a base observavel do sistema, depois o fluxo backend, a interface web e, por fim, os pontos de extensao para canais e arquiteturas futuras.

## 1. Fechar contratos da POC

Objetivo: estabilizar o vocabulario tecnico antes da implementacao.

Tarefas:

- Definir enums principais:
  - `ConversationStatus`
  - `MessageStatus`
  - `MessageDirection`
  - `AttachmentStatus`
  - `ProcessingEventType`
  - `ProcessingStatus`
  - `ChannelType`
  - `ArchitectureMode`
  - `RuntimeMode`
- Definir modelos compartilhados:
  - `Conversation`
  - `Message`
  - `Attachment`
  - `ProcessingEvent`
  - `ReviewTask`
  - `NormalizedInboundMessage`
  - `NormalizedOutboundMessage`
- Criar payloads de exemplo para:
  - criacao de conversa
  - envio de mensagem de texto
  - envio de mensagem com imagem
  - evento SSE
  - resposta final mockada
  - tarefa de revisao humana
- Registrar contratos em `packages/contracts`.

Criterio de sucesso: frontend e backend usam os mesmos nomes, status e payloads sem ambiguidade.

## 2. Preparar backend base

Objetivo: criar a API minima executavel.

Tarefas:

- Criar projeto FastAPI em `apps/api`.
- Configurar settings da aplicacao.
- Criar endpoint `GET /health`.
- Criar estrutura de rotas:
  - `conversations`
  - `messages`
  - `events`
  - `attachments`
- Criar schemas Pydantic equivalentes aos contratos.
- Criar camada inicial de servicos.

Criterio de sucesso: API sobe localmente e responde `GET /health`.

## 3. Implementar persistencia inicial

Objetivo: garantir rastreabilidade desde o primeiro fluxo funcional.

Tarefas:

- Configurar banco de dados.
- Criar tabelas:
  - `conversations`
  - `messages`
  - `attachments`
  - `processing_events`
  - `review_tasks`
- Implementar camada de acesso a dados.
- Criar migracoes iniciais.
- Persistir timestamps, status, metadata JSON e correlation IDs.

Criterio de sucesso: uma conversa criada pode ser inspecionada no banco.

## 4. Implementar conversas

Objetivo: habilitar o ciclo minimo de sessao.

Tarefas:

- Implementar `POST /conversations`.
- Implementar `GET /conversations/{conversation_id}`.
- Implementar `GET /conversations/{conversation_id}/messages`.
- Emitir evento `conversation.created`.
- Persistir metadados basicos da sessao.

Criterio de sucesso: conversa pode ser criada, recuperada e associada a eventos.

## 5. Implementar envio de mensagens com multipart

Objetivo: receber texto, anexos e metadados em um fluxo rastreavel.

Tarefas:

- Implementar `POST /messages`.
- Aceitar campos:
  - `conversationId`
  - `text`
  - `files[]`
  - `metadata_json`
- Validar arquivos:
  - tipo MIME
  - tamanho
  - quantidade
- Persistir mensagem inbound.
- Persistir anexos.
- Gerar `correlation_id`.
- Emitir eventos:
  - `message.received`
  - `attachment.upload.started`
  - `attachment.upload.completed`
  - `attachment.validation.started`
  - `attachment.validation.completed`

Criterio de sucesso: o backend salva mensagem, anexos e eventos a partir de uma requisicao multipart.

## 6. Criar storage local da POC

Objetivo: salvar anexos por adapter, sem acoplar o dominio ao mecanismo fisico.

Tarefas:

- Criar interface de storage.
- Implementar `LocalStorageAdapter`.
- Salvar arquivos em pasta controlada da POC.
- Gerar `storage_key`.
- Calcular checksum.
- Capturar metadados basicos da imagem:
  - tamanho em bytes
  - MIME
  - largura
  - altura

Criterio de sucesso: anexos sao salvos fisicamente e rastreados no banco.

## 7. Implementar event streaming com SSE

Objetivo: permitir que o frontend acompanhe o processamento em tempo real.

Tarefas:

- Criar `GET /conversations/{conversation_id}/events/stream`.
- Implementar publicacao interna de eventos.
- Persistir eventos antes ou durante a emissao.
- Enviar eventos no formato SSE.
- Suportar reconexao basica.
- Manter caminho para buscar eventos ja persistidos.

Criterio de sucesso: eventos persistidos chegam ao frontend em tempo real.

## 8. Implementar runtime mockado

Objetivo: simular agentes sem introduzir logica real de IA.

Tarefas:

- Criar `MockProcessingRuntime`.
- Simular fluxo:
  - `processing.started`
  - `actor.invoked` para `router_agent`
  - `actor.completed` para `router_agent`
  - `actor.invoked` para `faq_agent`, `stock_agent` ou `image_intake_agent`
  - `actor.progress`
  - `actor.completed`
  - `response.final`
  - `processing.completed`
- Criar resposta outbound mockada.
- Persistir mensagem final.
- Persistir duracao por etapa.
- Simular `review.required` em casos controlados.

Criterio de sucesso: cada mensagem gera uma sequencia de eventos e uma resposta final mockada.

## 9. Criar frontend base

Objetivo: preparar a aplicacao web para consumir a API real da POC.

Tarefas:

- Criar projeto Next.js em `apps/web`.
- Configurar TypeScript, Tailwind CSS e componentes base.
- Criar layout principal.
- Criar cliente HTTP em `lib/api`.
- Criar cliente SSE em `lib/sse`.
- Criar tipos em `lib/types`.

Criterio de sucesso: frontend sobe localmente e cria conversa via backend.

## 10. Implementar chat web

Objetivo: entregar o fluxo principal de interacao.

Tarefas:

- Criar lista de mensagens.
- Criar composer de texto.
- Criar uploader de imagem.
- Exibir preview antes do envio.
- Enviar multipart para `POST /messages`.
- Mostrar mensagens inbound e outbound.
- Exibir estados:
  - enviando
  - aceito
  - processando
  - concluido
  - erro

Criterio de sucesso: usuario envia texto/imagem e recebe resposta mockada.

## 11. Implementar timeline de eventos

Objetivo: tornar o processamento interno visivel.

Tarefas:

- Criar painel de eventos.
- Conectar ao endpoint SSE.
- Renderizar eventos em ordem cronologica.
- Exibir:
  - tipo do evento
  - ator
  - status
  - duracao
  - mensagem relacionada
  - payload resumido
- Diferenciar visualmente estados:
  - running
  - completed
  - failed
  - review required

Criterio de sucesso: o usuario acompanha visualmente o processamento interno da mensagem.

## 12. Criar adapters de canal

Objetivo: preparar a substituicao futura do Web Chat por WhatsApp.

Tarefas:

- Criar interface `ChannelAdapter`.
- Implementar `WebChatAdapter`.
- Criar `WhatsAppAdapter` stub.
- Criar modelos normalizados:
  - inbound
  - outbound
  - attachment
  - metadata
- Garantir que a application layer nao dependa diretamente do formato web.

Criterio de sucesso: a aplicacao processa mensagens normalizadas, nao payloads especificos do frontend.

## 13. Adicionar observabilidade e metadados

Objetivo: tornar cada execucao analisavel posteriormente.

Tarefas:

- Registrar:
  - `request_id`
  - `correlation_id`
  - `architecture_mode`
  - `runtime_mode`
  - `channel`
  - duracao total
  - duracao por etapa
- Separar metadados operacionais de contexto util ao modelo.
- Padronizar logs.
- Preparar base para replay e inspecao.

Criterio de sucesso: uma interacao pode ser reconstruida por banco, logs e eventos.

## 14. Criar fixtures e cenarios de teste

Objetivo: tornar a demonstracao e os testes reproduziveis.

Tarefas:

- Criar fixtures em `packages/test-fixtures`.
- Definir cenarios:
  - duvida recorrente
  - consulta de disponibilidade
  - imagem de produto
  - caso que exige revisao humana
  - erro de anexo
- Criar payloads de exemplo.
- Criar scripts simples para popular ou validar fluxo.

Criterio de sucesso: a POC pode ser demonstrada com casos consistentes.

## 15. Validar ponta a ponta

Objetivo: confirmar que a POC cumpre seu papel tecnico.

Tarefas:

- Testar criacao de conversa.
- Testar envio de mensagem texto.
- Testar envio de imagem valida.
- Testar rejeicao de imagem invalida.
- Testar stream SSE.
- Testar persistencia de eventos.
- Testar resposta final mockada.
- Testar refresh/reconexao do frontend.
- Verificar acesso ao historico.

Criterio de sucesso: a POC executa o fluxo completo sem operacoes manuais fora da aplicacao.

## Ordem resumida

1. Contratos compartilhados.
2. Backend FastAPI base.
3. Persistencia.
4. Conversas.
5. Mensagens e anexos.
6. Storage local.
7. SSE.
8. Runtime mockado.
9. Frontend base.
10. Chat com upload.
11. Timeline de eventos.
12. Adapters de canal.
13. Observabilidade.
14. Fixtures.
15. Validacao ponta a ponta.

