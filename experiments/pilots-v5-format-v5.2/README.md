# Formato v5.2: revisão uniforme, com decisões preservadas

A coleta B revisada produziu 150 execuções reais com entradas estáveis, sob o gerador architectural-comparison-v4.1. O juiz v5.1 produziu 149 avaliações primárias válidas e uma saída com `review_reason_codes` duplicado em `quality_reasons`, idêntico ao campo raiz. As 150 avaliações históricas e as 15 rechecagens permaneceram em seus diretórios originais.

V5.2 altera somente a configuração de normalização local e o identificador de versão. Modelo, parâmetros, prompt, schema, rubrica, fatos e critérios permanecem exatamente iguais. Um único passe determinístico remove cercas Markdown e a cópia do metadado somente quando existe um campo raiz com valor idêntico. Ausência do campo raiz, duplicatas conflitantes e outros defeitos não são arbitrados por essa regra. Nenhuma nota, justificativa, critério, violação ou campo de encaminhamento é reescrito.

A calibração técnica integral de 20 fixtures deve passar novamente. Em seguida, `normalize_automated_pilots.py` aplica a regra aos registros dos dois lotes e às rechecagens em diretórios novos. Toda avaliação válida anterior precisa permanecer exatamente igual depois da validação. O script recusa diferenças no prompt/schema/controles de inferência e divergência do pacote original do juiz. Journals e snapshots de inferência são preservados, acompanhados por ledger e snapshot do normalizador. Não há novas chamadas de agentes ou avaliações primárias nessa etapa; o consumo físico das saídas reutilizadas não é somado duas vezes.

Os dados/gabaritos/rubrica continuam em `experiments/pilots-v5`, preservados. A revisão não corrige entradas por reaproveitamento: as entradas estáveis já foram exercitadas nas 150 execuções reais do B. A normalização trata exclusivamente a estrutura da saída do avaliador, depois da coleta. O piloto bruto v5.1, com a falha de schema não resolvida, permanece como lote próprio.

```sh
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v5/calibration-v5.2 --calibrate
apps/agent-runtime/.venv/bin/python scripts/normalize_automated_pilots.py var/reports/automated-pilots-v5/pilot-b var/reports/automated-pilots-v5/pilot-b-format-v5.2 --calibration var/reports/automated-pilots-v5/calibration-v5.2
apps/agent-runtime/.venv/bin/python scripts/normalize_automated_pilots.py var/reports/automated-pilots-v5/historical-regrade var/reports/automated-pilots-v5/historical-regrade-format-v5.2 --calibration var/reports/automated-pilots-v5/calibration-v5.2
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v5/pilot-b-format-v5.2 --calibration var/reports/automated-pilots-v5/calibration-v5.2
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v5/historical-regrade-format-v5.2 --calibration var/reports/automated-pilots-v5/calibration-v5.2
```

A decisão sobre a matriz definitiva depende dos gates do novo B e de um conjunto próprio de cenários. Não constitui validação clínica. Farmacêuticos continuam opcionais; HTTP/banco, OCR e transferência humana não foram exercitados ao vivo.
