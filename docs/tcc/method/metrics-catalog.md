# Catálogo de métricas

| Métrica | Definição operacional | Unidade/agregação | Fonte |
|---|---|---|---|
| Sucesso técnico | execução concluída sem erro fatal | proporção por cenário e arquitetura | resultado da run |
| Latência | tempo entre início e conclusão da execução | ms; p50 e p95 | benchmark runner |
| Tokens de entrada | tokens enviados ao modelo | média, mediana e dispersão | telemetria do modelo |
| Tokens de saída | tokens gerados pelo modelo | média, mediana e dispersão | telemetria do modelo |
| Tokens totais | entrada + saída | média, mediana e dispersão | telemetria do modelo |
| Chamadas de ferramenta | ferramentas acionadas durante a run | contagem média | eventos `tool.started` |
| Erros de ferramenta | chamadas encerradas com falha | taxa e contagem | eventos de ferramenta |
| Loops | ciclos internos registrados pela arquitetura | contagem média | `loop_count` |
| Handoffs | transferências entre agentes | contagem média e distribuição | `handoff_count` |
| Revisão humana | execução marcada para revisão | proporção | `human_review_required` |
| Qualidade da resposta | aderência à rubrica aprovada | escala `TBD-OQ-002` | avaliadores definidos no protocolo |

Sucesso técnico não equivale a resposta correta. A comparação principal deverá reportar eficiência e qualidade separadamente. Valores ausentes não serão convertidos para zero; serão identificados e tratados conforme o motivo da ausência.
