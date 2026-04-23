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

## 16. Refinar eventos do runtime e metadados de anexos

Objetivo: completar lacunas dos contratos atuais sem alterar o fluxo principal da POC.

Tarefas:

- Emitir `actor.progress` no `MockProcessingRuntime`.
- Definir payload padrao para progresso de ator:
  - `step`
  - `message`
  - `progressPercent`
  - `actorName`
  - `architectureMode`
  - `runtimeMode`
- Persistir e publicar eventos de progresso pelo mesmo pipeline dos demais eventos.
- Extrair dimensoes de imagens aceitas:
  - `width`
  - `height`
- Persistir dimensoes em `attachments`.
- Manter checksum, MIME, tamanho e storage key como metadados obrigatorios.
- Atualizar fixtures para validar eventos de progresso e metadados de imagem.

Criterio de sucesso: o processamento mockado exibe progresso intermediario e anexos de imagem sao salvos com dimensoes rastreaveis.

## 17. Fortalecer replay e reconexao SSE

Objetivo: tornar o stream de eventos mais confiavel em refresh, queda temporaria de conexao e retomada de historico.

Tarefas:

- Suportar retomada por cursor ou `Last-Event-ID`.
- Enviar eventos persistidos posteriores ao ultimo evento conhecido ao reconectar.
- Manter heartbeat para conexoes abertas sem eventos.
- Evitar eventos duplicados no frontend durante reconexao.
- Persistir ordenacao estavel por `created_at` e `id`.
- Atualizar cliente SSE para:
  - armazenar ultimo evento recebido
  - recuperar backlog ao abrir conexao
  - sinalizar estados de reconexao
  - cair para polling pontual quando necessario
- Cobrir fluxo em fixture ou script E2E.

Criterio de sucesso: apos refresh ou queda de conexao, o frontend reconstrui a timeline sem perda ou duplicacao relevante de eventos.

## 18. Adicionar selecao de arquitetura no front

Objetivo: permitir que a POC comece a registrar qual modo arquitetural esta sendo exercitado em cada interacao.

Tarefas:

- Adicionar select de `architecture_mode` no frontend:
  - `centralized_orchestration`
  - `structured_workflow`
  - `decentralized_swarm`
- Enviar o modo selecionado na criacao de conversa e/ou no envio de mensagem.
- Persistir `architecture_mode` nos metadados da conversa, mensagem e eventos.
- Exibir o modo arquitetural ativo na UI.
- Garantir que o runtime mockado use o valor recebido nos payloads dos eventos.
- Atualizar contratos e exemplos quando necessario.

Criterio de sucesso: cada mensagem processada fica associada ao modo arquitetural escolhido pelo usuario e essa informacao aparece no historico de eventos.

## 19. Adicionar seguranca inicial da API

Objetivo: proteger a API da POC com controles simples, adequados para ambiente local e demonstracao controlada.

Tarefas:

- Adicionar configuracao por variaveis de ambiente para:
  - API key
  - secrets internos
  - URLs de servicos externos
  - credenciais de storage
- Criar `.env.example` sem valores sensiveis reais.
- Implementar validacao de API key para endpoints protegidos.
- Definir quais endpoints continuam publicos:
  - `GET /health`
  - documentacao local, quando habilitada
- Evitar commit de secrets reais.
- Documentar setup local de secrets.
- Atualizar cliente frontend para enviar a chave quando aplicavel em ambiente de desenvolvimento.

Criterio de sucesso: endpoints principais rejeitam chamadas sem credencial valida e o projeto continua executavel localmente com `.env.example`.

## 20. Evoluir storage para MinIO e S3 compativel

Objetivo: substituir o armazenamento puramente local por um adapter compativel com buckets, mantendo caminho simples para producao em S3 ou equivalente.

Tarefas:

- Adicionar MinIO ao ambiente local em `infra/docker`.
- Criar configuracoes de bucket para desenvolvimento.
- Criar adapter de storage S3 compativel.
- Manter `LocalStorageAdapter` como fallback ou modo simplificado.
- Definir settings para selecionar provider:
  - `local`
  - `minio`
  - `s3`
- Salvar arquivos em bucket com chave deterministica e rastreavel.
- Persistir provider, bucket e object key nos metadados do anexo quando necessario.
- Preparar documentacao para migrar de MinIO local para S3/cloud.
- Garantir que download/visualizacao de anexos continue funcionando pela API.

Criterio de sucesso: a POC salva e recupera anexos via MinIO local, sem acoplar o dominio ao provider fisico, e fica preparada para bucket cloud em producao.

## 21. Expandir formatos de anexo

Objetivo: permitir que o fluxo multimodal aceite mais formatos sem quebrar a validacao e a rastreabilidade existentes.

Tarefas:

- Passar a aceitar PDF alem de imagens.
- Revisar lista de MIME types permitidos.
- Definir limites por tipo de arquivo:
  - imagens
  - PDFs
- Persistir metadados especificos por tipo:
  - dimensoes para imagem
  - numero de paginas para PDF, quando viavel
  - tamanho em bytes
  - checksum
- Ajustar previews no frontend:
  - preview visual para imagem
  - card de arquivo para PDF
- Atualizar eventos de validacao para indicar tipo de anexo.
- Atualizar fixtures com PDF valido e PDF invalido.

Criterio de sucesso: o usuario consegue anexar PDF valido, o backend valida e persiste o arquivo, e a UI representa o anexo de forma clara.

## 22. Preparar ingestao de eventos do servico de IA

Objetivo: abrir um ponto de integracao para que um servico externo de IA publique eventos de processamento no mesmo historico da POC.

Tarefas:

- Criar endpoint protegido para receber eventos externos do servico de IA.
- Validar payload recebido contra os contratos de `ProcessingEvent`.
- Exigir identificadores de rastreabilidade:
  - `conversation_id`
  - `message_id`
  - `correlation_id`
  - `event_type`
  - `actor_name`, quando aplicavel
- Garantir idempotencia para evitar duplicacao de eventos.
- Persistir eventos recebidos antes de publica-los no SSE.
- Publicar eventos externos para assinantes ativos da conversa.
- Registrar origem do evento no payload ou metadata:
  - `mock_runtime`
  - `ai_service`
  - `system`
- Documentar contrato esperado para o servico de IA.

Criterio de sucesso: um servico externo consegue enviar eventos que aparecem na timeline do frontend e ficam persistidos no historico da conversa.

## 23. Validar escopo expandido da POC

Objetivo: confirmar que os novos requisitos nao quebraram o fluxo principal ja existente.

Tarefas:

- Testar `actor.progress` no runtime mockado.
- Testar captura de dimensoes de imagem.
- Testar envio e persistencia de PDF.
- Testar reconexao SSE com replay de eventos.
- Testar selecao de arquitetura no frontend e persistencia na API.
- Testar API key em endpoints protegidos.
- Testar storage MinIO local.
- Testar fallback ou configuracao alternativa de storage.
- Testar ingestao de evento externo do servico de IA.
- Atualizar scripts de validacao e documentacao operacional.

Criterio de sucesso: a POC expandida executa o fluxo completo com texto, imagem, PDF, eventos internos, eventos externos, storage por bucket, seguranca basica e reconexao confiavel.

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
16. Eventos de progresso e metadados de anexos.
17. Replay e reconexao SSE.
18. Selecao de arquitetura no frontend.
19. Seguranca inicial da API.
20. Storage MinIO e S3 compativel.
21. Novos formatos de anexo.
22. Ingestao de eventos do servico de IA.
23. Validacao do escopo expandido.
