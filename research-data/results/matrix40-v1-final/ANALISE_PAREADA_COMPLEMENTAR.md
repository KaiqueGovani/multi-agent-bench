# Análise pareada complementar

O procedimento geral Friedman, seguido de Wilcoxon e Holm, já constava da solicitação autoral e do protocolo documental. A implementação, o tratamento de empates/ausências e a lista operacional de sete métricas foram registrados **após a coleta**; estes resultados são complementares e exploratórios. Não modificam rótulos, gabaritos, código congelado ou gates de prontidão. Não apresentar como plano confirmatório integralmente pré-registrado.

Cada observação é uma mediana de cinco repetições por cenário/arquitetura. Só entram trios de arquiteturas com cinco valores observados em cada condição. Exclusões são explícitas em paired-statistics-provenance.json. As 600 execuções não são 600 amostras independentes. Casos de conteúdo qualitativo dependem do juiz técnico; não representam validação clínica.

| metric | paired_scenarios | friedman_statistic | friedman_p_chi_square | friedman_p_permutation_sensitivity | kendall_W | posthoc_triggered | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| end_to_end_latency_ms | 40 | 60.45 | 7.47221e-14 | 1e-05 | 0.755625 | True | calculated |
| total_tokens | 40 | 67.2 | 2.55685e-15 | 1e-05 | 0.84 | True | calculated |
| intent_adherence | 39 | 4.86957 | 0.0876168 | 0.08432 | 0.0624303 | False | calculated |
| operational_correctness | 38 | 1.9375 | 0.379557 | 0.39943 | 0.0254934 | False | calculated |
| safety | 39 | 0 | 1 | 1 | 0 | False | calculated |
| completeness | 39 | 2.77778 | 0.249352 | 0.28874 | 0.0356125 | False | calculated |
| clarity | 39 | 2 | 0.367879 | 0.52981 | 0.025641 | False | calculated |

A aproximação qui-quadrado do Friedman recebe uma análise de sensibilidade por permutação de rótulos dentro de cada cenário, devido às três condições. Empates são corrigidos; contraste totalmente constante é explicitamente identificado, com estatística 0 e p=1 por convenção, sem evidência de equivalência. [Documentação oficial do Friedman](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.friedmanchisquare.html).

| metric | architecture_a | architecture_b | paired_scenarios | nonzero_pairs | p_unadjusted | p_holm_within_metric | rank_biserial_b_minus_a | median_paired_difference | median_difference_bootstrap_95_low | median_difference_bootstrap_95_high |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| end_to_end_latency_ms | centralized_orchestration | structured_workflow | 40 | 40 | 1.81899e-12 | 5.45697e-12 | 1 | 8328.91 | 6658.08 | 9682.98 |
| end_to_end_latency_ms | centralized_orchestration | decentralized_swarm | 40 | 40 | 1.81899e-12 | 5.45697e-12 | 1 | 9283.88 | 7007.54 | 11422.7 |
| end_to_end_latency_ms | structured_workflow | decentralized_swarm | 40 | 40 | 0.0703392 | 0.0703392 | 0.329268 | 551.692 | -189.353 | 1429.55 |
| total_tokens | centralized_orchestration | structured_workflow | 40 | 40 | 1.81899e-12 | 5.45697e-12 | 1 | 3882.5 | 2794 | 4469.5 |
| total_tokens | centralized_orchestration | decentralized_swarm | 40 | 40 | 1.81899e-12 | 5.45697e-12 | 1 | 4645.5 | 3154 | 5919.5 |
| total_tokens | structured_workflow | decentralized_swarm | 40 | 40 | 0.00386751 | 0.00386751 | 0.514634 | 545.5 | 330.5 | 788 |

Wilcoxon bilateral é aplicado às três comparações somente quando o Friedman qui-quadrado é menor que 0,05; Holm corrige esses três p-valores dentro da métrica. Não há correção conjunta entre as sete métricas globais. Zeros são retirados, empates usam permutação de sinais e diferenças são arredondadas a 1e-9 antes dos ranks. [Documentação oficial do Wilcoxon](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.wilcoxon.html).

Efeitos e diferenças têm orientação arquitetura B menos A: maior latência/token representa mais consumo/tempo; maior nota representa pontuação maior sob a rubrica. Kendall W resume o contraste global; correlação bisserial de ranks resume o contraste pareado entre diferenças não nulas. Intervalos de 95% são percentis de 20.000 reamostragens pareadas de cenários, condicionais à amostra intencional; não garantem cobertura para todos os atendimentos. O Wilcoxon pressupõe simetria das diferenças sob a hipótese nula. Falha em rejeitar não prova equivalência. Sucesso binário, pass^1/pass^5 e encaminhamento permanecem descritivos, sem novo teste binário escolhido após observar resultados.
