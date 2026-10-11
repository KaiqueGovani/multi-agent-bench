# Pilotos automatizados — v4.3

Entrega concluída: A = 9 execuções; B = 150 execuções, 150 avaliações primárias e 15 rechecagens. A recomendação é realizar novo piloto após revisar os gabaritos e a consistência do juiz. Não iniciar as 600 execuções. Ver os relatórios locais em `var/reports/automated-pilots-v4/{pilot-a,pilot-b}/preliminary-results.md`.

As execuções mediram `architectural-comparison-v4`, preservado em `code-snapshot`. O código atual é candidato `architectural-comparison-v4.1`: remove IDs administrativos e URLs dos descritores de anexos, usando aliases estáveis. Essa correção passou em teste de igualdade de contexto entre conversas novas, mas ainda não foi medida em inferência real. Na coleta v4, conteúdo, fontes e estado de domínio eram comuns; descritores continham IDs de mensagem diferentes. Não afirmar igualdade literal de todas as entradas históricas. A análise posterior `descriptive-analysis-v4.3.2` trata uma contradição interna do juiz como desconhecida e esclarece exportações; os registros e avaliações primárias permanecem intactos.

Aplicar [emenda autoral](AMENDMENT.md). Os reference-* são cópias da branch documental origin/agent/tcc-ralph-setup, sem mesclagem. Nenhuma alteração do manuscrito/gates. Casos sintéticos e gabaritos pré-fechados; revisão técnica por schema/fontes/regras, com apoio LLM, sem revisão farmacêutica.

A coleta utiliza o núcleo real do runtime em processos isolados, com inferência Bedrock real e ferramentas simuladas determinísticas. Não inicia HTTP/API/PostgreSQL. Centralizada: supervisor único; workflow sequencial; swarm com bootstrap coordenado, handoffs entre especialistas e síntese sequencial. Políticas e capacidades comuns; distribuição de ferramentas e contexto intermediário pertence à arquitetura. Histórico estruturado integral, anexos somente descritores, com a ressalva de IDs descrita acima. Modelo/SDK, fontes, papéis, parâmetros, schema/rubrica e código efetivo congelados por lote. Não reutilizar as rodadas antigas ou aquecimento como A/B.

## Comandos históricos da coleta

Estes comandos documentam a coleta concluída com o código congelado v4. Não os usar para acrescentar resultados v4.1 aos diretórios existentes: a retomada recusa deriva de código. Uma rodada futura precisa de diretório e versão próprios, referências revisadas e nova calibração se o juiz mudar. Credencial válida permanece em arquivo privado; não sincronizar dependências durante coleta.

```sh
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v4/connectivity --connectivity
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v4/calibration-v4.3 --calibrate
apps/agent-runtime/.venv/bin/python scripts/run_research_pilot.py --cases experiments/pilots-v4/pilot-a.json --case A-operational --output var/reports/automated-pilots-v4/warmup --max-tokens 2048
apps/agent-runtime/.venv/bin/python scripts/run_research_pilot.py --cases experiments/pilots-v4/pilot-a.json --output var/reports/automated-pilots-v4/pilot-a --repetitions 1 --max-tokens 2048 --continue-after-failure
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v4/pilot-a --judge --calibration var/reports/automated-pilots-v4/calibration-v4.3
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v4/pilot-a --calibration var/reports/automated-pilots-v4/calibration-v4.3
```

Só iniciar B após revisar calibração e readiness do piloto A; resolver defeitos de infraestrutura primeiro. Sucesso de tarefa baixo não é motivo para refazer unidades. Falhas e cortes permanecem no lote e denominadores. A autorização cobre B, não 600.

```sh
apps/agent-runtime/.venv/bin/python scripts/run_research_pilot.py --cases experiments/pilots-v4/pilot-b.json --output var/reports/automated-pilots-v4/pilot-b --repetitions 5 --max-tokens 2048 --continue-after-failure
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v4/pilot-b --judge --calibration var/reports/automated-pilots-v4/calibration-v4.3
apps/agent-runtime/.venv/bin/python scripts/judge_automated_pilots.py var/reports/automated-pilots-v4/pilot-b --recheck --calibration var/reports/automated-pilots-v4/calibration-v4.3
apps/agent-runtime/.venv/bin/python scripts/analyze_automated_pilots.py var/reports/automated-pilots-v4/pilot-b --calibration var/reports/automated-pilots-v4/calibration-v4.3
```

Runner aceita --plan-only e --resume. Retomada recusa deriva de código/SDK; não repete unidades terminais nem avaliações válidas desfavoráveis. O lock impede dois runners no mesmo lote; não usar dois lotes simultâneos. Falha interrompida sem terminal exige inspeção do processo antes de qualquer substituição. Timeout encerra grupo de processos e confirma saída antes da unidade seguinte. Retries de infraestrutura externa/reexecução de bloco não são automáticos; implementar nova rodada com vínculos explícitos se vierem a ser autorizados, preservando a permutação.

## Instrumentos e interpretação

Sucesso é a conjunção do terminal técnico, cada requisito, fonte obrigatória e ausência de violação crítica. Verificador objetivo confere ferramentas, argumentos e resultado, incluindo omissão. O juiz semântico recebe o pacote comum de fontes e resposta sem condições/metadados; não pode sobrepor falha objetiva. Task success null permanece desconhecido. Encaminhamento explícito e cinco dimensões são separados; não há nota geral. Calibração técnica 12 fixtures, no máximo uma tentativa de reparo de formato (cercas de Markdown podem ser removidas deterministicamente sem mudar decisões). Primeira calibração v4.1 falhou por formato e nome livre de dimensão; foi preservada e substituída por schema com campos explícitos em v4.3. A segunda calibração teve 11/12 concordâncias, pois uma omissão foi tratada como violação crítica. v4.3 esclarece que omissão/incerteza não equivale a afirmação falsa, e recalibra integralmente. Uma fixture incompleta foi clarificada para evitar inferência de disponibilidade implícita; versão anterior permanece arquivada.

Pass^1 e pass^5 usam as cinco classificações de cada cenário; cobertura e limites no conjunto planejado são exportados. Rechecagem tem uma seleção por arquitetura×estrato, 15 respostas; primeiras notas permanecem principais. Métricas contínuas e ordinais são resumidas por cenário e depois entre cenários. Sem Friedman/Wilcoxon no piloto; plano definitivo documental permanece futuro. Não alegar independência das cinco respostas com temperatura zero. Sem custo USD enquanto não houver tarifa regional/perfil/cache confirmada; consumo do juiz separado e projeção linear de tokens explícita.

Os arquivos de dados locais ficam ignorados em var/reports. Artefatos principais: manifest.json, execution-order.csv, runs.jsonl/csv, calls.jsonl, events.jsonl, responses.jsonl, evaluations.jsonl, aggregated-evaluations.jsonl, metrics.csv, architecture-stratum-metrics.csv, review-queue.csv, preliminary-results.md. attempts.jsonl e judge-attempts.jsonl são journals append-only; CSV/JSON agregados são exportações derivadas reconstruíveis. code-snapshot e assets-snapshot congelam fontes/gabaritos/instruções. Interpretação multimodal/OCR e integração HTTP/banco continuam fora da capacidade demonstrada.

## Auditoria farmacêutica opcional

O piloto B produziu 14 pacotes sensíveis aprovados, com cobertura das três arquiteturas, dentro do teto inicial de 24 respostas; nenhum flag farmacêutico ficou fora. A contradição do juiz é revisão técnica. Nenhum farmacêutico avaliou esses pacotes. O arquivo `focused-pharmacist-template.csv` pede apenas segurança, encaminhamento, suspeita crítica e justificativa; `NA` indica campo não julgável. Cada um dos dois profissionais, se disponíveis posteriormente, pode preencher uma cópia independentemente com ID pseudônimo distinto, sem nome pessoal. Não usar o template amplo legado para esta auditoria focalizada.

```sh
apps/agent-runtime/.venv/bin/python scripts/import_focused_reviews.py var/reports/automated-pilots-v4/pilot-b /caminho/privado/revisoes-preenchidas.csv
```

O importador valida respostas selecionadas, campos e duplicatas, preserva rótulos humanos separados em `human-focused-reviews.jsonl` e registra a cobertura em `human-focused-review-summary.json`. Não modifica avaliações LLM nem simula consenso. A atualização documental futura deve citar essa cobertura efetiva; os relatórios históricos continuam descrevendo a coleta sem revisão humana. A amostra direcionada não estima erro representativo nem concordância geral.
