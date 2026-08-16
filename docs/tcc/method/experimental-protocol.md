# Protocolo experimental do MAB

Status: rascunho operacional, ainda não congelado. Versão inicial: 2026-08-16.

## 1. Objetivo

Comparar orquestração centralizada, workflow estruturado e coordenação descentralizada por handoffs sob cenários equivalentes de atendimento farmacêutico. O protocolo mede diferenças de eficiência, coordenação, qualidade e necessidade de revisão, sem presumir qual arquitetura será superior.

## 2. Unidade experimental

A unidade experimental é uma execução de um cenário por uma arquitetura, com versão do código, modelo, parâmetros, ferramentas e limites registrados. Uma repetição corresponde a uma nova execução da mesma combinação cenário-arquitetura.

## 3. Arquiteturas

- `centralized_orchestration`: supervisor único seleciona ferramenta, interpreta o retorno e produz a resposta.
- `structured_workflow`: etapas fixas de classificação, evidência, revisão e síntese, com etapa multimodal quando aplicável.
- `decentralized_swarm`: coordenador inicia a cadeia, especialistas podem realizar handoffs entre pares e um sintetizador produz a resposta final.

## 4. Cenários

O conjunto inicial deve cobrir, no mínimo: perguntas frequentes; consulta de estoque; anexos; mensagens de continuação; solicitações que exigem revisão humana; entradas ambíguas; indisponibilidade de ferramenta; e contexto composto por mais de uma intenção. Cada caso terá identificador, texto de entrada, histórico necessário, anexos sintéticos ou anonimizados, rota esperada, ferramentas esperadas, risco e critérios de qualidade.

Origem definitiva dos cenários de WhatsApp: `TBD-OQ-001`. Enquanto a questão estiver aberta, somente fixtures sintéticas e esquemas sem conteúdo real são permitidos.

## 5. Controles

Devem permanecer constantes: commit do repositório, modelo e versão, região, parâmetros de geração, conjunto de ferramentas, base de FAQ/estoque, limites de timeout e handoff, cenário e condições de infraestrutura. A ordem das execuções deverá ser randomizada ou contrabalanceada para reduzir efeitos de aquecimento e variação temporal.

## 6. Repetições e tamanho amostral

Número de repetições por combinação: `TBD antes do congelamento`. A decisão deverá considerar variabilidade observada em um piloto separado, precisão desejada e custo de execução. Resultados do piloto não serão misturados aos testes definitivos.

## 7. Métricas

Primárias propostas: qualidade da resposta, taxa de sucesso técnico e latência p50/p95. Secundárias: tokens totais, chamadas e erros de ferramentas, loops, handoffs e taxa de revisão humana. A rubrica de qualidade depende da OQ-002. Definições operacionais completas ficam em `metrics-catalog.md`.

## 8. Procedimento

1. Validar o schema dos cenários e impedir dados identificáveis.
2. Registrar commit, configuração, modelo e versão das ferramentas.
3. Executar piloto técnico para verificar instrumentação; não interpretar como resultado.
4. Congelar protocolo, cenários, rubrica e número de repetições.
5. Executar a matriz cenário × arquitetura × repetição.
6. Preservar logs técnicos e resultados em ambiente apropriado, sem dados pessoais no GitHub público.
7. Verificar integridade, execuções faltantes e falhas antes da análise.
8. Calcular métricas conforme fórmulas versionadas.
9. Submeter resultados aos autores antes de solicitar abertura do evidence gate.

## 9. Reprodutibilidade

Cada lote deverá registrar timestamp UTC, commit SHA, configuração, modelo, versão das ferramentas, identificador de cenário, arquitetura, repetição, modo mock/live, duração, contagens de eventos e localização dos artefatos. Segredos, prompts com dados pessoais e conteúdo bruto não serão preservados em repositório público.

## 10. Critérios de exclusão

Uma execução poderá ser excluída apenas por falha de infraestrutura documentada, violação do protocolo, cenário corrompido ou perda de telemetria necessária. Exclusões devem permanecer no log com justificativa; não podem ser removidas por desempenho desfavorável.

## 11. Gates

Este protocolo não abre os capítulos 7, 8 ou 9. Os gates continuam fechados até existirem dados anonimizados, execuções reproduzíveis, métricas calculadas, revisão dos autores e autorização humana explícita.
