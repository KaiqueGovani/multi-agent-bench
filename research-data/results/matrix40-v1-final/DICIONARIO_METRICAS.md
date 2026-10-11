# Dicionário de métricas e denominadores

A unidade experimental é uma execução de um cenário em uma arquitetura. A unidade de comparação pareada é o cenário: 40 cenários, cada um com cinco repetições por arquitetura. Há 200 unidades planejadas por arquitetura. Valores ausentes não significam zero.

| Campo ou tabela | Definição e denominador |
| --- | --- |
| technical_successes | Execuções terminadas com resposta e registro técnico completo; não comprova resolução da tarefa. |
| task_successes / task_failures / task_unknown | Classificação pelo agregador congelado: término técnico, critérios essenciais, evidências obrigatórias e violações críticas. As três contagens somam as unidades planejadas. |
| known_task_success_rate | Sucessos / unidades com classificação conhecida. A cobertura e os desconhecidos devem acompanhar essa taxa. |
| content_successes | Reaplica o agregador retirando somente a exigência de consultas obrigatórias. Mantém critérios semânticos, coerência do juiz e verificações de violações críticas. Não é a nota operacional de 1–5. |
| procedure_applicable | Unidades cujo gabarito exige pelo menos uma consulta: 19 cenários × cinco repetições = 95 por arquitetura. Sem obrigação, procedimento é NA. |
| procedure_successes / procedure_evaluable | Todas as consultas obrigatórias satisfeitas / unidades aplicáveis cujo procedimento é conhecido. Compatibilidade de ferramenta, argumentos e retorno integra a verificação. |
| metrics.csv | 120 grupos cenário × arquitetura. Cada mediana contínua usa as observações não ausentes das cinco repetições; denominadores e êxitos técnicos acompanham o grupo. |
| *_median_of_case_medians | Mediana das 40 medianas de cenário para uma arquitetura. Não é necessariamente a mediana das 200 execuções. |
| pass^1 | Média da fração de sucessos nas cinco repetições por cenário completamente avaliável. Informar complete_scenarios. |
| pass^5 | Proporção dos cenários completamente avaliáveis com todas as cinco repetições aprovadas. Não significa ao menos uma aprovação em cinco tentativas. |
| pass_*_lower / pass_*_upper | Limites descritivos que consideram desconhecidos no conjunto planejado. Não são intervalos de confiança. |
| paired-comparisons.csv | Calcula diferença e razão das medianas primeiro dentro de cada cenário e resume os 40 pares. Mediana das razões não é razão das medianas globais. |
| quality-summary.csv | Contagens das notas 1–5 e NA em cada uma das cinco dimensões. Denominador planejado de 200 por arquitetura; não há nota geral. |
| referral_TP / TN / FP / FN | Recomendação explícita observada versus indicação técnica congelada. FP não demonstra inadequação clínica. Campos incoerentes ou avaliação ausente permanecem desconhecidos. |
| critical-violation-counts.csv | Número de respostas sinalizadas por categoria e fonte objetiva/juiz. As fontes podem sobrepor-se; não somar como respostas distintas. |
| failure-diagnostic-summary.csv | Verificações objetivas e indicadores candidatos de falha de processo. Ausência de indicação não demonstra ausência do mecanismo; indicadores candidatos não estabelecem causalidade. |
| resource-consumption.json | Chamadas físicas e tokens conhecidos registrados pelo provedor, separados em geração, julgamento, rechecagem e conectividade. Inclui reparos de formato. Registros por processo e consolidados são cópias das mesmas chamadas. |
| readiness.json | Gates congelados. Coleta completa e avaliação integralmente pronta são propriedades diferentes; qualquer gate pendente deve ser descrito, não reinterpretado como aprovado. |

O tempo dos agentes inclui inicialização e execução por processos/arquivos, e exclui juiz, HTTP e banco de produção. Custos monetários não verificados são indisponíveis. Segurança, indicação de encaminhamento e gabaritos pertencem ao escopo técnico; nenhuma revisão farmacêutica foi realizada.
