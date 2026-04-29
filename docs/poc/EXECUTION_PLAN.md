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

## 24. Definir contratos de execucao por run

Objetivo: introduzir `run` como unidade analitica de cada execucao de resposta, sem duplicar a telemetria detalhada do servico de IA.

Tarefas:

- Definir modelo `Run` como ponte entre:
  - `conversation_id`
  - `message_id`
  - `correlation_id`
  - `external_run_id`
  - `ai_session_id`
  - `trace_id`
- Definir status de run:
  - `pending`
  - `running`
  - `completed`
  - `failed`
  - `cancelled`
  - `human_review_required`
- Definir metadados experimentais obrigatorios:
  - `architecture_key`
  - `architecture_version`
  - `model_provider`
  - `model_name`
  - `model_version`
  - `prompt_bundle_version`
  - `toolset_version`
  - `experiment_id`
  - `scenario_id`
- Definir payload de criacao de run e payload de conclusao de run.
- Atualizar contratos compartilhados e exemplos.

Criterio de sucesso: existe contrato claro para vincular uma mensagem a uma execucao comparavel, independente do backend de telemetria usado pelo servico de IA.

## 25. Implementar persistencia de runs no chat-api

Objetivo: salvar no banco transacional o estado resumido de cada execucao, mantendo o detalhe tecnico no servico de IA e no OpenTelemetry.

Tarefas:

- Criar tabela `runs`.
- Associar `runs` a `conversations` e `messages`.
- Persistir:
  - IDs de rastreabilidade
  - configuracao experimental
  - status
  - inicio e fim da execucao
  - duracao total
  - necessidade de revisao humana
  - resultado final resumido
  - `summary_json`
- Criar migracao Alembic.
- Criar schemas Pydantic para run.
- Expor run em detalhes da conversa quando aplicavel.

Criterio de sucesso: cada mensagem processada pode ter uma ou mais execucoes registradas e consultadas pelo chat-api.

## 26. Criar handoff do chat-api para o servico de IA

Objetivo: preparar o chat-api para acionar um servico externo de IA/Strands usando `run_id` como contrato de execucao.

Tarefas:

- Criar adapter ou client para o servico de IA.
- Criar run com status `pending` antes de chamar o servico externo.
- Enviar ao servico de IA:
  - `conversation_id`
  - `message_id`
  - `run_id`
  - `correlation_id`
  - `ai_session_id`
  - `architecture_key`
  - `model_key`
  - `traceparent`, quando disponivel
- Manter runtime mockado como fallback local.
- Atualizar status do run para `running` apos aceite do servico externo.
- Tratar falha de dispatch com status `failed` e evento visivel na timeline.

Criterio de sucesso: o chat-api consegue criar uma execucao e despacha-la para um servico externo sem acoplar a logica da conversa ao Strands.

## 27. Propagar contexto OpenTelemetry e baggage

Objetivo: permitir rastreamento distribuido entre chat-api, servico de IA e backend de observabilidade.

Tarefas:

- Gerar ou receber `traceparent` no chat-api.
- Persistir `trace_id` no run quando disponivel.
- Propagar `traceparent` para o servico de IA.
- Definir baggage minimo:
  - `conversation_id`
  - `message_id`
  - `run_id`
  - `architecture_key`
  - `model_key`
  - `experiment_id`
- Evitar dados sensiveis ou payloads grandes no baggage.
- Documentar quais atributos devem virar spans, logs e metricas no servico de IA.

Criterio de sucesso: uma execucao pode ser rastreada do chat-api ao servico de IA por `run_id` e `trace_id`.

## 28. Consolidar resumo e metricas agregadas por run

Objetivo: receber do servico de IA um resumo de execucao suficiente para comparacao futura, sem armazenar todos os spans no banco transacional.

Tarefas:

- Criar endpoint para atualizar/concluir run.
- Receber resumo do servico de IA com:
  - status final
  - `external_run_id`
  - `trace_id`
  - duracao total
  - tempo ate primeiro evento publico
  - tempo ate primeira resposta parcial, quando houver
  - tokens de entrada
  - tokens de saida
  - tokens totais
  - quantidade de tool calls
  - quantidade de erros de ferramenta
  - quantidade de loops
  - `stop_reason`
  - necessidade de revisao humana
  - resultado final
- Persistir dados agregados no run ou em tabela `run_metrics`.
- Emitir evento publico quando o run for concluido ou falhar.

Criterio de sucesso: cada run possui resumo suficiente para comparacao por modelo, arquitetura, prompt e toolset.

## 29. Versionar configuracoes experimentais

Objetivo: garantir que comparacoes futuras entre arquiteturas e modelos sejam reproduziveis.

Tarefas:

- Definir taxonomia para:
  - `architecture_family`
  - `architecture_key`
  - `architecture_version`
  - `routing_strategy`
  - `memory_strategy`
  - `tool_executor_mode`
  - `review_policy_version`
- Registrar versoes de modelo, prompt e ferramentas.
- Associar runs a `experiment_id` e `scenario_id`.
- Atualizar fixtures para informar `scenario_id`.
- Criar exemplos de runs para:
  - orquestracao centralizada
  - workflow estruturado
  - swarm descentralizado
- Documentar criterio minimo para comparacao experimental.

Criterio de sucesso: duas execucoes podem ser comparadas sabendo exatamente qual configuracao experimental gerou cada resultado.

## 30. Integrar runs aos eventos externos do servico de IA

Objetivo: fazer com que eventos externos publicados pelo servico de IA sejam associados a uma execucao especifica.

Tarefas:

- Adicionar `run_id` ao contrato de ingestao de eventos externos.
- Validar se o run pertence a `conversation_id` e `message_id`.
- Persistir `run_id` nos eventos ou no payload estruturado.
- Atualizar idempotencia considerando `run_id` e `external_event_id`.
- Permitir eventos de origem:
  - `mock_runtime`
  - `ai_service`
  - `system`
- Atualizar SSE para entregar eventos com referencia ao run.
- Atualizar documentacao de `POST /integrations/ai/events`.

Criterio de sucesso: eventos do Strands/servico de IA aparecem na timeline vinculados a conversa, mensagem e run corretos.

## 31. Implementar historico de conversas na UI

Objetivo: transformar a interface de chat em uma experiencia persistente, capaz de mostrar e organizar multiplas conversas.

Tarefas:

- Criar endpoint para listar conversas recentes.
- Retornar dados resumidos por conversa:
  - `conversation_id`
  - status
  - canal
  - `architecture_mode`
  - ultima atualizacao
  - ultima mensagem ou resumo curto
  - contagem de mensagens
  - contagem de eventos
  - ultimo `run_id`
  - indicativo de revisao humana pendente
- Criar menu lateral retratil no frontend.
- Exibir conversas recentes no menu lateral.
- Permitir criar nova conversa sem perder acesso ao historico.
- Diferenciar visualmente conversas ativas, concluidas, com erro e com revisao humana.

Criterio de sucesso: o usuario consegue ver uma lista de conversas recentes e iniciar uma nova conversa mantendo o historico acessivel.

## 32. Permitir retomada de conversa existente

Objetivo: permitir que o usuario selecione uma conversa antiga e reconstitua seu estado completo na UI.

Tarefas:

- Carregar conversa selecionada pelo menu lateral.
- Buscar mensagens, anexos, eventos, runs e tarefas de revisao da conversa.
- Reabrir o stream SSE da conversa selecionada.
- Manter deduplicacao de eventos ao alternar entre conversas.
- Atualizar composer, timeline e status visual com base na conversa ativa.
- Evitar misturar mensagens/eventos entre conversas diferentes.
- Garantir que uma conversa com processamento em andamento continue recebendo eventos apos ser retomada.

Criterio de sucesso: o usuario consegue alternar entre conversas e cada conversa exibe seu historico, anexos, runs e timeline corretamente.

## 33. Implementar painel de revisao humana

Objetivo: tornar visivel e acionavel o estado de supervisao humana previsto no modelo de dominio.

Tarefas:

- Criar endpoint para listar tarefas de revisao abertas.
- Criar endpoint para resolver tarefa de revisao.
- Associar revisao humana ao run que gerou a necessidade de intervencao.
- Permitir registrar:
  - status final
  - observacao humana
  - responsavel, quando disponivel
  - horario de resolucao
- Exibir painel ou aba de revisao humana na UI.
- Mostrar motivo da revisao, mensagem original, anexos, run e eventos relacionados.
- Permitir marcar tarefa como resolvida.
- Emitir evento de sistema ao resolver revisao.
- Atualizar status da conversa, mensagem e run quando a revisao for resolvida.

Criterio de sucesso: uma conversa encaminhada para revisao humana pode ser identificada, analisada e resolvida pela interface.

## 34. Criar tela de inspecao da conversa e do run

Objetivo: oferecer uma visao tecnica para demonstracao, auditoria e analise experimental.

Tarefas:

- Criar tela ou modo de inspecao para a conversa ativa.
- Exibir metadados da conversa, mensagens, anexos e runs.
- Exibir metadados do run:
  - `run_id`
  - `external_run_id`
  - `ai_session_id`
  - `trace_id`
  - modelo
  - arquitetura
  - prompt bundle
  - toolset
  - status
  - duracao
- Exibir eventos com payload JSON expandivel.
- Exibir link ou referencia para trace externo quando disponivel.
- Separar metadados operacionais de contexto util ao modelo.
- Permitir copiar IDs relevantes para depuracao.

Criterio de sucesso: uma interacao pode ser auditada pela UI sem acessar diretamente banco, logs ou backend de tracing.

## 35. Adicionar filtros e controles avancados na timeline

Objetivo: melhorar a leitura do processamento quando houver muitos eventos, atores, runs e fontes externas.

Tarefas:

- Filtrar eventos por:
  - run
  - tipo de evento
  - ator
  - status
  - mensagem relacionada
  - origem do evento
- Permitir expandir e recolher payloads.
- Permitir alternar entre timeline resumida e detalhada.
- Destacar eventos de erro, revisao humana e eventos externos.
- Manter ordenacao cronologica estavel.
- Preservar filtros ao atualizar a conversa ativa, quando fizer sentido.

Criterio de sucesso: o usuario consegue reduzir ruido da timeline e investigar eventos especificos sem perder contexto.

## 36. Criar dashboard operacional e experimental da POC

Objetivo: apresentar uma visao agregada da POC para demonstracao, acompanhamento e comparacao inicial entre configuracoes.

Tarefas:

- Criar endpoint de metricas agregadas.
- Exibir cards com:
  - total de conversas
  - total de runs
  - runs concluidos
  - runs com erro
  - runs com revisao humana
  - total de mensagens
  - total de anexos
  - total de eventos
  - tempo medio de processamento
- Exibir distribuicao por:
  - `architecture_key`
  - `model_name`
  - `scenario_id`
  - tipo de anexo
- Permitir acessar conversas e runs relevantes a partir do dashboard.

Criterio de sucesso: a POC apresenta indicadores basicos de uso e comparacao experimental sem consulta manual ao banco.

## 37. Implementar replay visual de processamento

Objetivo: permitir demonstrar uma execucao ja concluida reproduzindo os eventos persistidos em ordem temporal.

Tarefas:

- Criar modo de replay na timeline.
- Permitir replay por conversa ou por run.
- Reproduzir eventos persistidos em ordem cronologica.
- Permitir pausar, retomar e reiniciar replay.
- Permitir controlar velocidade de reproducao.
- Preservar a timeline real sem alterar eventos persistidos.
- Diferenciar visualmente replay de processamento ao vivo.

Criterio de sucesso: uma conversa ou run concluido pode ter seu processamento visualmente reproduzido a partir dos eventos salvos.

## 38. Melhorar galeria e visualizacao de anexos

Objetivo: melhorar a experiencia de analise de imagens e documentos recebidos nas conversas.

Tarefas:

- Criar galeria de anexos por conversa.
- Permitir abrir imagem em visualizacao ampliada.
- Exibir card especifico para PDF.
- Mostrar metadados tecnicos:
  - MIME
  - tamanho
  - checksum
  - dimensoes da imagem
  - paginas do PDF
  - storage provider
- Indicar status de validacao do anexo.
- Exibir mensagem clara para anexos rejeitados ou indisponiveis.

Criterio de sucesso: anexos de uma conversa podem ser inspecionados visualmente e tecnicamente pela UI.

## 39. Criar tela de configuracoes da POC

Objetivo: deixar explicitas as configuracoes ativas do ambiente sem exigir leitura de codigo ou variaveis locais.

Tarefas:

- Criar endpoint de configuracao publica segura.
- Expor apenas configuracoes nao sensiveis:
  - ambiente
  - API base URL
  - `runtime_mode`
  - storage provider
  - limites de upload
  - formatos aceitos
  - `architecture_mode` padrao
  - integracao externa de IA habilitada ou nao
- Criar tela de configuracoes no frontend.
- Ocultar secrets, credenciais e chaves reais.
- Documentar diferenca entre configuracoes publicas e secrets internos.

Criterio de sucesso: o usuario consegue verificar pela UI quais modos, limites e integracoes estao ativos na POC, sem expor informacoes sensiveis.

## 40. Validar observabilidade e comparacao experimental

Objetivo: confirmar que a nova camada de runs realmente permite comparacao futura entre modelos, arquiteturas e cenarios.

Tarefas:

- Testar criacao de run por mensagem.
- Testar vinculo `conversation_id -> message_id -> run_id`.
- Testar dispatch mockado para servico de IA.
- Testar propagacao de `traceparent` e baggage minimo.
- Testar ingestao de eventos externos com `run_id`.
- Testar conclusao de run com metricas agregadas.
- Testar dashboard por arquitetura, modelo e scenario.
- Atualizar fixtures com cenarios comparaveis.
- Atualizar documentacao de validacao.

Criterio de sucesso: a POC consegue demonstrar uma execucao rastreavel por run e produzir dados minimos para comparacao experimental futura.

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
24. Contratos de execucao por run.
25. Persistencia de runs.
26. Handoff para servico de IA.
27. Propagacao OpenTelemetry e baggage.
28. Resumo e metricas agregadas por run.
29. Versionamento experimental.
30. Runs nos eventos externos do servico de IA.
31. Historico de conversas na UI.
32. Retomada de conversa existente.
33. Painel de revisao humana.
34. Tela de inspecao da conversa e do run.
35. Filtros avancados na timeline.
36. Dashboard operacional e experimental da POC.
37. Replay visual de processamento.
38. Galeria e visualizacao de anexos.
39. Tela de configuracoes da POC.
40. Validacao de observabilidade e comparacao experimental.
