# Organizacao inicial da POC

Esta estrutura foi pensada para a primeira fase da POC: contratos, backend minimo, frontend de chat, eventos de processamento e base para adapters de canal. Ela deixa espaco para as futuras logicas de agentes sem misturar a POC com os experimentos finais.

```txt
.
  apps/
    api/
      app/
        api/
          routes/
        domain/
          attachments/
          channels/
          conversations/
          events/
          messages/
          review/
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
    web/
      src/
        app/
        components/
          chat/
          events/
        hooks/
        lib/
          api/
          sse/
          types/
  docs/
    poc/
  infra/
    docker/
    postgres/
    storage/
  packages/
    contracts/
    test-fixtures/
  scripts/
```

## apps/api

Backend FastAPI da POC.

- `api/routes`: endpoints HTTP e SSE.
- `domain`: modelos e regras de dominio independentes de framework.
- `services`: casos de uso da aplicacao, como criar conversa e receber mensagem.
- `adapters`: entrada, saida, storage e streaming isolados do nucleo.
- `runtime/mock`: simulacao dos atores e do fluxo de processamento.
- `db`: configuracao de persistencia, sessoes e migracoes futuramente.
- `schemas`: contratos Pydantic expostos pela API.
- `core`: configuracoes, constantes, logging e utilitarios transversais.

## apps/web

Frontend Next.js da POC.

- `components/chat`: layout, lista de mensagens, composer e upload/preview.
- `components/events`: timeline e indicadores de processamento.
- `lib/api`: cliente HTTP para conversas, mensagens e anexos.
- `lib/sse`: cliente SSE e reconexao.
- `lib/types`: tipos usados pelo frontend.
- `hooks`: hooks de conversa, envio de mensagem e stream de eventos.

## packages/contracts

Espaco para contratos compartilhados entre backend e frontend. A ideia e manter aqui enums, payloads e exemplos que precisam ficar sincronizados entre camadas.

## packages/test-fixtures

Dados ficticios e casos de teste usados pela POC: mensagens de exemplo, eventos simulados, imagens pequenas e cenarios de atendimento.

## docs/poc

Documentacao especifica desta fase. O handoff original foi movido para `docs/poc/HANDOFF.md` para preservar o contexto completo sem transformar o `AGENTS.md` raiz em documento de requisitos.

## infra

Arquivos de infraestrutura local da POC.

- `docker`: composicao local e configuracoes auxiliares.
- `postgres`: scripts ou configuracoes especificas do banco.
- `storage`: configuracoes para storage local, MinIO ou S3 compativel.

## scripts

Automacoes de desenvolvimento, carga de dados, verificacoes locais e utilitarios de manutencao.

## Proximos passos sugeridos

1. Criar os contratos iniciais em `packages/contracts`.
2. Criar os schemas Pydantic equivalentes em `apps/api/app/schemas`.
3. Implementar o backend minimo com persistencia e SSE.
4. Implementar o frontend com chat e timeline de eventos.
5. Adicionar fixtures para validar o fluxo mockado de ponta a ponta.

