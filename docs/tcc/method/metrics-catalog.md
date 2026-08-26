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
| Encaminhamento correto | concordância entre a decisão do sistema e o gabarito profissional | proporção | gabarito validado por farmacêutico |
| Falso negativo de segurança | revisão profissional necessária, mas não solicitada pelo sistema | proporção | gabarito validado por farmacêutico |
| Sensibilidade de encaminhamento | proporção de cenários que exigem revisão e são corretamente encaminhados | proporção com intervalo de confiança quando aplicável | gabarito e saída da execução |
| Especificidade de encaminhamento | proporção de cenários que não exigem revisão e são corretamente tratados sem encaminhamento | proporção com intervalo de confiança quando aplicável | gabarito e saída da execução |
| Qualidade da resposta | aderência à intenção, correção operacional, segurança, completude e clareza | cinco critérios ordinais de 1 a 5 | *LLM-as-Judge* em todas as respostas e avaliação humana cega amostral |

Sucesso técnico não equivale a resposta correta. A comparação principal deverá reportar eficiência, coordenação, qualidade e segurança separadamente. Valores ausentes não serão convertidos para zero; serão identificados e tratados conforme o motivo da ausência.

O modelo e a versão do *LLM-as-Judge*, a versão da rubrica e o *prompt* de avaliação serão congelados antes da avaliação definitiva. Todas as 120 respostas do estrato de revisão profissional serão avaliadas por farmacêutico, além de uma amostra estratificada de 20% das respostas dos demais estratos.
