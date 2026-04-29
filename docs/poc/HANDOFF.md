# Handoff para Codex — POC de Front-end + Back-end do TCC

## 1) Contexto do projeto

Trata-se de um TCC sobre **sistema multiagente para atendimento inteligente em farmácias**, com foco em **comparar arquiteturas de coordenação** entre agentes em um ambiente experimental.

Nesta fase, **não será implementada a lógica real dos agentes**. O objetivo imediato é construir a **base de interação com o usuário**: uma interface de chat multimodal e um back-end preparado para receber mensagens, arquivos e emitir eventos de processamento de forma transparente.

A arquitetura final do TCC deverá permitir, futuramente, a comparação entre três abordagens:

* orquestração centralizada
* workflow estruturado
* organização descentralizada / swarm

A POC atual deve ser construída pensando em:

* rastreabilidade
* observabilidade
* persistência de conversas e eventos
* possibilidade de supervisão humana
* facilidade de troca do canal web por WhatsApp no futuro

---

## 2) Escopo desta fase

### Dentro do escopo

* Interface web de chat
* Input de texto
* Input de imagem
* Upload e preview de imagem
* Envio de metadados úteis ao back-end
* Painel visual mostrando o que o back-end está fazendo
* Persistência de mensagens, anexos e eventos
* Estrutura de canal desacoplada da lógica principal
* Runtime mockado emitindo eventos de processamento

### Fora do escopo por enquanto

* implementação real dos agentes especializados
* integração real com LLMs
* decisão clínica real
* automação farmacêutica completa
* comparação experimental entre arquiteturas

---

## 3) Objetivo técnico da POC

Construir uma base que permita, mais adiante, plugar diferentes arquiteturas de coordenação sem reescrever o front ou a infraestrutura principal.

A POC deve provar que:

1. o usuário consegue interagir por texto e imagem
2. o sistema mantém sessões e histórico
3. o back-end consegue emitir eventos granulares do processamento
4. a interface consegue refletir esses eventos visualmente
5. o núcleo da aplicação é independente do canal de entrada

---

## 4) Requisitos funcionais

1. O usuário deve poder iniciar uma conversa.
2. O usuário deve poder enviar mensagens de texto.
3. O usuário deve poder anexar uma ou mais imagens por mensagem.
4. O sistema deve validar formato e tamanho dos arquivos.
5. O sistema deve exibir preview da imagem antes ou após envio.
6. O front-end deve mostrar o histórico da conversa.
7. O front-end deve exibir uma timeline ou painel de eventos do processamento.
8. O back-end deve emitir eventos em tempo real durante o processamento.
9. O sistema deve persistir mensagens, anexos e eventos.
10. O sistema deve suportar status como:

* recebido
* validando anexo
* processando
* repassado
* aguardando
* concluído
* erro
* encaminhado para revisão humana

11. O sistema deve associar cada ação a uma conversa e a uma mensagem.
12. O sistema deve permitir futura substituição do canal web por WhatsApp sem refatoração estrutural severa.

---

## 5) Requisitos não funcionais

1. O sistema deve ser observável.
2. O sistema deve ser rastreável ponta a ponta.
3. O sistema deve ser modular.
4. O sistema deve ser extensível para novos canais.
5. O sistema deve ser suficientemente simples para uma POC acadêmica.
6. O sistema deve usar dados fictícios / simulados nesta fase.
7. O sistema deve permitir replay ou inspeção do histórico de eventos futuramente.
8. O sistema deve separar telemetria operacional de contexto útil ao modelo.

---

## 6) Stack sugerida

### Front-end

* Next.js
* React
* TypeScript
* Tailwind CSS
* shadcn/ui

### Back-end

* FastAPI
* Python
* Pydantic

### Persistência

* PostgreSQL

### Arquivos

* MinIO ou S3 compatível

### Comunicação em tempo real

* SSE (Server-Sent Events)

### Motivação dessa escolha

* HTTP multipart é ótimo para texto + imagem
* SSE é suficiente para stream de eventos de processamento do back-end para a UI
* FastAPI facilita contratos bem tipados, upload e documentação
* a separação por adapters ajuda muito na futura troca para WhatsApp

---

## 7) Arquitetura proposta

### Visão macro

* Web Chat Adapter
* Application Layer
* Processing Runtime (mockado nesta fase)
* Persistence Layer
* File Storage
* Event Streaming Layer
* Future Channel Adapter: WhatsApp

### Fluxo principal

1. Usuário envia texto + imagem pelo front
2. Front chama endpoint HTTP multipart
3. Back cria/recupera conversa
4. Back persiste mensagem e anexos
5. Back emite eventos em stream
6. Runtime mockado simula etapas internas
7. Front recebe e renderiza a timeline de processamento
8. Back persiste resposta final
9. Front atualiza chat

---

## 8) Decisão arquitetural central

O núcleo do sistema **não deve saber se a origem da mensagem é Web Chat ou WhatsApp**.

Deve existir um modelo interno normalizado de mensagem. Cada canal deve apenas:

* transformar entrada externa em modelo interno
* enviar para a aplicação
* transformar saída interna em formato do canal

---

## 9) Modelo de domínio inicial

### Conversation

* id
* channel
* created_at
* updated_at
* status
* user_session_id
* metadata_json

### Message

* id
* conversation_id
* direction (inbound | outbound | system)
* content_text
* created_at_client
* created_at_server
* status
* correlation_id
* metadata_json

### Attachment

* id
* message_id
* storage_key
* original_filename
* mime_type
* size_bytes
* checksum
* width
* height
* created_at

### ProcessingEvent

* id
* conversation_id
* message_id
* event_type
* actor_name
* parent_event_id
* correlation_id
* payload_json
* created_at
* duration_ms
* status

### ReviewTask

* id
* conversation_id
* message_id
* reason
* status
* created_at
* resolved_at

---

## 10) Eventos que o sistema deve suportar desde já

Mesmo sem agentes reais, o sistema deve emitir eventos como se eles existissem.

### Event types sugeridos

* conversation.created
* message.received
* attachment.upload.started
* attachment.upload.completed
* attachment.validation.started
* attachment.validation.completed
* processing.started
* actor.invoked
* actor.progress
* actor.completed
* actor.failed
* handoff.requested
* review.required
* response.partial
* response.final
* processing.completed

### Exemplo de atores mockados

* router_agent
* faq_agent
* stock_agent
* image_intake_agent
* supervisor_agent

Esses atores podem ser apenas simulados nesta fase.

---

## 11) Metadados recomendados

### Coletados no front

* client_timestamp
* timezone
* locale
* user_agent
* device_type
* upload_duration_ms
* message_input_duration_ms
* file_count
* file_types
* file_sizes
* conversation_id
* message_id temporário do cliente

### Operacionais do back-end

* correlation_id
* request_id
* processing_start_at
* processing_end_at
* total_duration_ms
* step_duration_ms
* channel
* architecture_mode
* runtime_mode (mock | real)
* review_required

### Possivelmente úteis ao modelo depois

* idioma
* horário atual
* contexto resumido da conversa
* tipo de anexo
* intenção inferida

Importante: nem todo metadado operacional deve ir para o prompt do modelo.

---

## 12) Etapas de implementação

# Etapa 1 — Fechar contratos

## Objetivo

Definir claramente os contratos de dados antes de construir a aplicação.

## Entregáveis

* schemas de Conversation, Message, Attachment, ProcessingEvent e ReviewTask
* enumerações de status
* enumerações de event_type
* definição do modelo interno normalizado de canal
* documento curto com payloads de exemplo

## Critério de pronto

Todos os fluxos principais cabem nos contratos sem ambiguidade.

---

# Etapa 2 — Backend mínimo funcional

## Objetivo

Criar a API base com persistência e stream de eventos.

## Endpoints sugeridos

* POST /conversations
* GET /conversations/{conversation_id}
* GET /conversations/{conversation_id}/messages
* POST /messages
* GET /conversations/{conversation_id}/events/stream
* GET /health

## Comportamento esperado

* aceitar texto + imagem
* persistir dados
* iniciar processamento mockado
* emitir eventos SSE
* devolver resposta final simulada

## Critério de pronto

É possível enviar uma mensagem, ver os eventos e receber uma resposta final.

---

# Etapa 3 — Front-end do chat

## Objetivo

Construir a interface de uso.

## Componentes sugeridos

* chat layout
* message list
* message composer
* image uploader
* upload preview
* send button
* event timeline / activity panel
* connection status indicator
* error toast / feedback visual

## Critério de pronto

O usuário consegue enviar texto e imagem e acompanhar o processamento visualmente.

---

# Etapa 4 — Persistência, métricas e observabilidade

## Objetivo

Transformar a POC em base experimental confiável.

## Itens

* salvar histórico completo de mensagens
* salvar anexos e metadados
* salvar eventos internos
* registrar duração por etapa
* registrar modo arquitetural em uso
* registrar necessidade de revisão humana
* preparar estrutura para análise posterior

## Critério de pronto

Cada interação pode ser reconstituída depois a partir do banco.

---

# Etapa 5 — Preparação para múltiplos canais

## Objetivo

Deixar a arquitetura pronta para futura integração com WhatsApp.

## Itens

* criar interface ChannelAdapter
* implementar WebChatAdapter
* criar WhatsAppAdapter stub
* normalizar inbound/outbound messages
* isolar lógica de transformação de mídia
* isolar lógica de status/eventos por canal

## Critério de pronto

O núcleo não depende diretamente do front web.

---

## 13) Estrutura de pastas sugerida

### Front-end

```txt
apps/web/
  src/
    app/
    components/chat/
    components/events/
    lib/api/
    lib/sse/
    lib/types/
    hooks/
```

### Back-end

```txt
apps/api/
  app/
    api/
      routes/
    domain/
      conversations/
      messages/
      attachments/
      events/
      review/
      channels/
    services/
    adapters/
      inbound/
      outbound/
      storage/
      streaming/
    runtime/
      mock/
    db/
    schemas/
    core/
```

---

## 14) Contratos iniciais de API

### POST /conversations

Cria uma nova conversa.

Resposta:

```json
{
  "conversationId": "uuid",
  "status": "active",
  "channel": "web_chat",
  "createdAt": "2026-04-22T10:00:00Z"
}
```

### POST /messages

Request multipart:

* conversationId
* text
* files[]
* metadata_json

Response:

```json
{
  "messageId": "uuid",
  "conversationId": "uuid",
  "status": "accepted",
  "correlationId": "uuid"
}
```

### SSE /conversations/{conversation_id}/events/stream

Eventos no formato:

```json
{
  "eventId": "uuid",
  "eventType": "actor.invoked",
  "actorName": "router_agent",
  "messageId": "uuid",
  "conversationId": "uuid",
  "status": "running",
  "createdAt": "2026-04-22T10:00:01Z",
  "payload": {
    "reason": "classifying incoming request"
  }
}
```

---

## 15) Backlog inicial priorizado

### P0

* definir schemas do domínio
* criar tabela de conversas
* criar tabela de mensagens
* criar tabela de anexos
* criar tabela de eventos
* endpoint de criação de conversa
* endpoint de envio de mensagem com multipart
* upload para storage local ou S3 compatível
* stream SSE por conversa
* runtime mockado emitindo eventos
* tela web básica de chat
* timeline visual de eventos

### P1

* preview de imagens
* retries / tratamento de erro no stream
* indicadores visuais por status
* página de histórico de conversa
* revisão humana como estado de sistema
* métricas por etapa

### P2

* adapter stub de WhatsApp
* replay de conversa
* painel simples de inspeção
* filtros de eventos
* alternância futura de architecture_mode

---

## 16) Fluxo mockado de processamento

Quando uma mensagem chegar, o sistema pode simular algo como:

1. message.received
2. attachment.validation.started
3. attachment.validation.completed
4. processing.started
5. actor.invoked (router_agent)
6. actor.completed (router_agent)
7. actor.invoked (faq_agent)
8. actor.completed (faq_agent)
9. response.final
10. processing.completed

Isso já permite construir o front com boa fidelidade.

---

## 17) Riscos a evitar

* acoplar front diretamente à lógica interna futura dos agentes
* misturar metadados operacionais com prompt de modelo sem critério
* usar WebSocket para tudo sem necessidade clara
* não persistir eventos de processamento
* não criar correlation_id por mensagem
* tratar o chat como simples request/response sem trilha intermediária

---

## 18) Definições práticas para a equipe

### Decisões já assumidas

* o canal inicial será web chat
* haverá input de texto e imagem
* haverá feedback visual do processamento interno
* o back-end será preparado para futura troca de canal
* os agentes reais serão ignorados nesta fase
* o runtime inicial será mockado

### Open questions que ainda podem ser fechadas depois

* quantas imagens por mensagem serão aceitas
* tamanho máximo por imagem
* quais formatos de imagem serão aceitos
* haverá autenticação já nesta POC ou não
* haverá multiusuário real ou apenas sessão local

---

## 19) Pedido de execução para o Codex

Codex, implemente a base desta POC respeitando estas prioridades:

1. contratos e tipos compartilhados
2. back-end mínimo com persistência e SSE
3. front-end de chat com timeline de eventos
4. runtime mockado com atores simulados
5. arquitetura preparada para futuros adapters de canal

Não implemente ainda lógica real de agentes, LLMs ou regras farmacêuticas avançadas. Foque em arquitetura, contratos, observabilidade e UX do fluxo.

---

## 20) Resultado esperado desta fase

Ao final desta fase, deverá existir uma aplicação em que:

* o usuário abre o chat
* envia texto e imagem
* acompanha visualmente o processamento interno
* recebe uma resposta final mockada
* tudo fica salvo para análise futura
* a base está pronta para receber agentes reais e novos canais depois
