# multi-agent-bench

Repositorio do TCC sobre sistema multiagente para atendimento inteligente em farmacias, com foco em comparar arquiteturas de coordenacao entre agentes.

A fase atual e uma POC de interacao e observabilidade: chat web multimodal, backend preparado para receber texto/imagem, persistencia de conversas e eventos, stream SSE e runtime mockado.

## Estrutura inicial

- `apps/api`: backend FastAPI da POC.
- `apps/web`: frontend Next.js da POC.
- `packages/contracts`: contratos compartilhados e payloads normalizados.
- `packages/test-fixtures`: dados ficticios e cenarios de teste.
- `docs/poc`: handoff, decisoes e documentacao da POC.
- `infra`: infraestrutura local, banco e storage.
- `scripts`: utilitarios de desenvolvimento.

Veja `docs/poc/STRUCTURE.md` para a descricao completa.

## Plano da POC

O plano cronologico de execucao esta em `docs/poc/EXECUTION_PLAN.md`.
