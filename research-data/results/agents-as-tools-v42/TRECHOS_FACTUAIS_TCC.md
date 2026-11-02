# Trechos factuais para revisão do TCC

Este documento complementa o relatório e não substitui o TCC, o Report 6 ou os relatórios anteriores. Os resultados abaixo pertencem exclusivamente ao experimento `d9d924d1-a45b-4778-baf3-b9f842bd2111`, protocolo `architectural-comparison-v4.2`, com geração congelada no commit `a0dd5bbaeef04fb8e9065cba3a7bcc48a5295a55`.

## Metodologia e implementação observada

Foram executadas 600 unidades novas: os mesmos 40 cenários revisados, cinco repetições e três configurações, com oito cenários em cada categoria e dificuldades 15/15/10. O cenário é a unidade pareada; as cinco repetições permanecem agrupadas. Históricos, descritores de anexos, fontes controladas e gabaritos foram mantidos por hash. Os gabaritos foram usados exclusivamente na avaliação; os agentes receberam somente o contexto original e a política comum.

A centralizada oferece três ferramentas `@tool`, que invocam agentes Strands reais de FAQ, estoque e anexos. O supervisor escolhe suas chamadas por inferência, recebe seus retornos e produz a resposta final. Não acessa diretamente as ferramentas de domínio e não usa sintetizador adicional. A fábrica de especialistas compartilha competências, parâmetros e fontes nas três condições; o swarm acrescenta a extensão explícita de delegação entre especialistas. A memória do mesmo especialista pode persistir dentro de uma tentativa, com isolamento entre cenários, repetições e arquiteturas.

Na centralizada, 135/200 unidades cumpriram o contrato e produziram 185 invocações reais de especialistas como ferramentas, com 185 retornos registrados. Nas outras 65 unidades o supervisor respondeu sem delegar: essas ocorrências foram preservadas, identificadas como violações e reprovadas no sucesso da tarefa. Não foram acrescentadas chamadas artificiais. Workflow e swarm cumpriram o contrato nas 200 unidades de cada condição. No swarm, 351 delegações registradas se dividem em 320 delegações iniciais do coordenador e 31 entre especialistas; tentativas de ferramentas e transferências efetivamente registradas são contadores distintos.

A geração foi sequencial no transporte histórico direto do núcleo, com blocos balanceados e semente 20261011. Utilizou Haiku 4.5, região us-west-2, temperatura zero e máximo de 2.048 tokens por requisição, com limites globais de 20 requisições, 20 consultas de domínio e 180 segundos por tentativa. O teto central foi seis invocações de especialistas e o teto legado do swarm seis delegações. Não houve fallback mock ou retries automáticos de inferência. Foram preservadas todas as primeiras tentativas.

O julgamento usou Sonnet 4.5, temperatura zero e máximo de 4.096 tokens. A pedido explícito do autor, antes do primeiro julgamento principal, seu despacho passou a quatro processos exclusivos por resposta. A geração permaneceu sequencial e suas latências não mudaram de fronteira. Modelo, referências, rubrica e sistema do julgador permaneceram iguais; SHA-256 `ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36`. O juiz não recebeu arquitetura, custo, latência ou trajetórias. O verificador objetivo conferiu separadamente ferramenta de domínio, argumento, retorno íntegro e execução real do especialista.

As 600 primeiras saídas do juiz continham cercas Markdown: 599 foram normalizadas localmente sob a regra de serialização já congelada; uma exigiu uma requisição adicional de reparo exclusivamente de formato. Assim, 600 avaliações principais finais válidas correspondem a 601 requisições físicas, e não a 600 primeiras saídas JSON estritas. Os registros brutos e os reparos foram preservados, sem escolha de julgamento mais favorável. As 15 rechecagens usaram 15 requisições, normalizadas localmente, e não substituíram os julgamentos principais.

## Resultados observados

Houve 600 términos técnicos, 535 conformidades arquiteturais, 600 avaliações principais válidas no esquema, nenhuma contradição interna detectada pelo verificador e nenhum sucesso de tarefa desconhecido. O sucesso da tarefa exigiu conclusão técnica, contrato arquitetural, requisitos de conteúdo, ausência de marcação crítica e comprovação das consultas obrigatórias. Foram observados 323 sucessos e 277 falhas.

| architecture | planned | technical_successes | architectural_compliant | task_successes | task_failures | task_unknown | content_successes | content_evaluable | mandatory_evidence_applicable | mandatory_evidence_compliant |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| centralized_orchestration | 200 | 200 | 135 | 84 | 116 | 0 | 140 | 200 | 95 | 56 |
| structured_workflow | 200 | 200 | 200 | 117 | 83 | 0 | 130 | 200 | 95 | 40 |
| decentralized_swarm | 200 | 200 | 200 | 122 | 78 | 0 | 127 | 200 | 95 | 45 |

As taxas observadas de sucesso da tarefa foram 42,0% na centralizada, 58,5% no workflow e 61,0% no swarm. Conteúdo e procedimento são medidas separadas: as consultas obrigatórias foram completamente comprovadas em 56/95, 40/95 e 45/95 execuções aplicáveis, respectivamente. As 105 unidades restantes por condição não exigiam consulta obrigatória; isso não equivale a consulta realizada. Uma chamada a um especialista, por si só, não satisfaz esse verificador.

| architecture | complete_scenarios | pass_1_complete | pass_5_complete | latency_ms_median_of_case_medians | end_to_end_latency_ms_median_of_case_medians | total_tokens_total | model_requests_total | actual_agents_total | agent_invocations_total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| centralized_orchestration | 40 | 0.4200 | 0.3750 | 6434.2410 | 7681.7774 | 1119765 | 642 | 385 | 385 |
| structured_workflow | 40 | 0.5850 | 0.5250 | 10437.3010 | 11539.3523 | 1272607 | 916 | 715 | 715 |
| decentralized_swarm | 40 | 0.6100 | 0.6000 | 10452.8804 | 11581.5365 | 1482146 | 937 | 720 | 751 |

Pass¹ é a média das proporções de sucesso nas cinco tentativas por cenário; pass⁵ é a proporção de cenários com cinco sucessos. As 40 séries por condição estão completas. Latência do núcleo e latência do coletor são medianas das medianas por cenário. O campo histórico `end_to_end_latency_ms` inclui processo, importações, núcleo e arquivos; não mede latência da API ou da interface em produção.

As diferenças de sucesso, orientadas como B menos A, foram estimadas em pontos percentuais com 20.000 reamostragens de cenários completos. Os testes pareados bilaterais de sinais por permutação usaram enumeração exata até 16 diferenças não nulas, ou 99.999 permutações com ajuste plus-one; Holm corrigiu as três comparações. A semente foi 20261011.

| architecture_a | architecture_b | difference_pp_b_minus_a | bootstrap_95_low_pp | bootstrap_95_high_pp | p_holm_three_comparisons |
| --- | --- | --- | --- | --- | --- |
| centralized_orchestration | structured_workflow | 16.5000 | -1.0000 | 34.0000 | 0.1700 |
| centralized_orchestration | decentralized_swarm | 19.0000 | 0.5000 | 37.0000 | 0.1700 |
| structured_workflow | decentralized_swarm | 2.5000 | -3.0000 | 9.0000 | 0.6250 |

As diferenças estimadas foram +16,5 pontos percentuais para workflow versus centralizada, +19,0 para swarm versus centralizada e +2,5 para swarm versus workflow. Nenhuma comparação rejeitou a hipótese nula no critério bilateral corrigido por Holm de 5%. O intervalo percentil do contraste swarm–centralizada e o teste por permutação usam procedimentos distintos; não selecionar o resultado mais favorável. Os testes pressupõem permutabilidade dos sinais sob a hipótese nula. Falha em rejeitar não demonstra equivalência.

As classes principais de falha são exclusivas: 65 violações arquiteturais, 117 falhas conjuntas de conteúdo e consulta obrigatória, 73 falhas somente de conteúdo e 22 somente de consulta, somando 277. Marcações críticas e sinais de procedimento adicionais são sobrepostos e não devem ser somados a essas classes.

## Consumo e custo estimado

A geração reconciliou 2.495 requisições físicas únicas: 3.368.241 tokens de entrada + 506.277 de saída = 3.874.518 tokens. O julgamento principal reconciliou 601 requisições: 3.804.446 de entrada + 556.911 de saída = 4.361.357 tokens. A rechecagem reconciliou 15 requisições e 106.089 tokens. Não houve consumo desconhecido nessas fases. Métricas acumuladas do pai e dos filhos não foram somadas novamente.

As estimativas em USD para o lote principal são US$ 6,4895886 de geração, US$ 21,7437033 de julgamento e US$ 0,5260101 de rechecagem, totalizando US$ 28,7593020. Somando piloto, integração pela API e conectividade, o consumo observado foi estimado em US$ 29,5464202. O piloto foi estimado em US$ 0,7386511, a integração em US$ 0,0482548 e a conectividade em US$ 0,0002123. Esses valores não são cobrança efetiva.

Foram usadas tarifas públicas padrão de inferência geográfica US, região de chamada us-west-2: Haiku 4.5 a US$ 1,10/5,50 por milhão de tokens de entrada/saída e Sonnet 4.5 a US$ 3,30/16,50. A fonte e a data de consulta 02/11/2026 constam no [registro de tarifas](../../../experiments/architectural-comparison-v42/pricing.json) e em resource-consumption.json; a lista oficial consultada informa vigência em 27/05/2026. Descontos da conta, créditos e cobrança real não foram verificados.

O custo principal combinado por sucesso observado foi estimado em US$ 0,10894520 na centralizada, US$ 0,08248685 no workflow e US$ 0,08161429 no swarm, incluindo julgamento e rechecagem. Os custos somente de geração, as parcelas de entrada/saída e os valores por unidade aparecem separadamente nas tabelas; esses escopos não são intercambiáveis.

## Rechecagem, integração e limites

As 15 respostas foram escolhidas antes da geração por uma regra fixa de categoria × arquitetura. Houve uma mudança de classificação na rechecagem do mesmo juiz; o primeiro julgamento foi preservado. Não se trata de avaliação humana nem de revisão farmacêutica.

A integração foi validada em quatro casos sintéticos de FAQ, estoque, anexos e múltiplas fontes, pela API, callbacks persistidos, replay SSE e interface, com especialistas reais e retornos observáveis. O piloto de engenharia teve seis casos × três arquiteturas: 18 términos técnicos, 17 conformidades arquiteturais, 18 avaliações válidas e 12 sucessos de tarefa. Essas fases permanecem fora das 600 unidades.

A amostra é intencional, conhecida, com fontes e gabaritos técnicos controlados. Anexos fornecem metadados; não há OCR, leitura de receitas, ERP real ou transferência humana efetiva. O lote não é validação clínica, não é teste externo independente e não teve revisão farmacêutica. A indicação comum de encaminhamento é uma política provisória, não uma demonstração de identificação clínica autônoma.

A máquina foi compartilhada com verificações de apresentação durante parte da geração, sem inferência paralela; a carga de CPU não foi medida sistematicamente. O coletor é sensível à carga local e o provedor também varia. As comparações de latência ficam limitadas a essa fronteira experimental.

O julgador original registra início UTC e duração monotônica com fronteiras diferentes. A reconstrução aproximada de intervalos apresentou quatro sobreposições aparentes de 47–60 ms entre chamadas consecutivas do mesmo trabalhador. Os registros não foram remarcados. Quatro PIDs exclusivos e chamadas síncronas sequenciais por trabalhador foram verificados; essa aproximação não prova um quinto processo nem fornece timestamps exatos de término no provedor. A limitação está preservada na auditoria restrita.

A tabela histórica é separada. A antiga centralizada corresponde a agente único e o sucesso antigo não incluía o novo campo técnico de contrato arquitetural. Não se agregaram execuções antigas e novas, nem se atribui causalidade à diferença histórica. TCC, Report 6 e relatórios anteriores não foram sobrescritos.

## Fontes e inventário para a escrita

Prompts estáticos, hashes, esquemas e placeholders: [static-definition.json](../../../experiments/architectural-comparison-v42/static-definition.json). Matriz das arquiteturas, diagrama e política de memória: [ARCHITECTURE.md](../../../experiments/architectural-comparison-v42/ARCHITECTURE.md). Validação e emenda do julgamento: [VALIDATION.md](../../../experiments/architectural-comparison-v42/VALIDATION.md) e [JUDGE_DISPATCH_AMENDMENT.md](../../../experiments/architectural-comparison-v42/JUDGE_DISPATCH_AMENDMENT.md).

`units.csv/jsonl` conserva uma linha por cada uma das 600 combinações; `scenario-metrics.csv` agrupa as 120 séries cenário × arquitetura. As tabelas de categoria, dificuldade, notas, críticas, consistência, falhas, custos e coordenação são quantitativas sanitizadas. Cinco figuras estão em SVG e PNG. `FILES.json` fornece tamanhos e hashes.

O pacote restrito conserva manifestos, plano de análise, contextos, gabaritos, código congelado, dependências, ordem, primeiras respostas, trajetórias, avaliações brutas, rechecagens, auditorias, comandos, piloto e integração. Os 15 exemplos descritivos completos, selecionados por regra lexical antes do julgamento sem consultar resultados, ficam em `trajectory-examples/EXEMPLOS_TRAJETORIAS.md/json`; o CSV público contém somente aliases e contadores. As evidências descrevem consultas, delegações e retornos observados, sem atribuir causas internas ao modelo.
