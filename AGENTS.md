# AGENTS.md

Este repositorio abriga a POC do TCC e, futuramente, as logicas dos agentes e os experimentos comparativos de arquiteturas de coordenacao.

## Contexto rapido

- Projeto: sistema multiagente para atendimento inteligente em farmacias.
- Foco do TCC: comparar arquiteturas de coordenacao entre agentes.
- Foco da POC atual: chat multimodal, persistencia, eventos SSE, observabilidade e runtime mockado.
- Fora do escopo agora: agentes reais, LLMs, regras clinicas avancadas e decisao farmaceutica real.

## Documentacao principal

- Handoff original da POC: `docs/poc/HANDOFF.md`
- Organizacao inicial da POC: `docs/poc/STRUCTURE.md`
- Plano de execucao da POC: `docs/poc/EXECUTION_PLAN.md`

## Diretriz de arquitetura

O nucleo da aplicacao nao deve depender do canal de entrada. Web Chat, WhatsApp ou qualquer canal futuro devem ser adapters que convertem mensagens externas para um modelo interno normalizado.

## Commits

Quando for solicitado criar commits neste repositorio, use mensagens claras, em ingles, seguindo Conventional Commits. Exemplos: `feat(api): add conversation schema`, `docs(poc): document initial architecture`, `fix(web): handle SSE reconnect`.
