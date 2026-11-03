# Revisão humana e análise da v4.3

O desfecho primário avalia o conteúdo final. A resposta deve cumprir todos os requisitos essenciais, recomendar a revisão profissional quando exigida e respeitar as restrições críticas. Conclusão técnica, conformidade arquitetural, consulta obrigatória e sucesso composto são desfechos separados. O [plano pré-coleta](analysis-plan.json) fixa as regras e a amostra de revisão.

## Pré-seleção e cadernos cegos

Após criar o manifesto com `--plan-only` e antes de iniciar a coleta, execute o primeiro comando. A seleção sorteia dois cenários por estrato e uma repetição compartilhada pelas três arquiteturas. O arquivo gerado vincula as 30 unidades ao manifesto e ao script usados. Após a geração concluir todas as disposições em `runs.jsonl`, execute o segundo comando.

```sh
python3 scripts/human_review_v43.py plan --cohort "$COHORT_V43"
python3 scripts/human_review_v43.py packet --cohort "$COHORT_V43"
```

O diretório privado `human-review-v43` contém `reviewer-a`, `reviewer-b` e o mapa de coordenação. O responsável pela pesquisa deve entregar apenas a pasta correspondente a cada revisor humano, separadamente. Preserve o mapa, os resultados automáticos e o caderno da outra pessoa no armazenamento restrito. Cada caderno contém a solicitação, o histórico, os metadados de anexos, a referência técnica congelada e a resposta. Os IDs opacos e a ordem são específicos de cada revisor. Rótulos literais das condições são ocultados. O texto ainda pode sugerir a condição, e o formulário permite registrar essa percepção.

Cada pessoa usa `INSTRUCOES.md` para preencher `responses.csv`, `criteria.csv` e `attestation.json`. As decisões devem ser individuais, sem assistência de modelo ou consulta à outra avaliação. O responsável pode usar pseudônimos distintos e deve guardar os formulários submetidos. A atestação registra as declarações dos revisores. A identidade e a independência não são verificadas pelo software.

Depois de receber os dois formulários reais, consolide-os localmente. `REVISOR_A` e `REVISOR_B` apontam para cópias devolvidas dos respectivos cadernos. Campos em branco permanecem pendentes. Uma resposta indisponível permanece na amostra planejada. Um rótulo de consenso exige duas decisões conhecidas e iguais.

```sh
python3 scripts/human_review_v43.py score --cohort "$COHORT_V43" \
  --reviewer-a "$REVISOR_A" --reviewer-b "$REVISOR_B" \
  --output "$COHORT_V43/human-scores.json"
```

## Análise automática e integração das avaliações humanas

Execute após consolidar os eventos, os julgamentos e `aggregated-evaluations.jsonl` conforme o [README da coleta](README.md). `PYTHON_ANALISE` aponta para um ambiente com NumPy, como `research-data/local/figures-env/bin/python`. Os comandos são locais e cada destino de saída deve ser novo.

```sh
"$PYTHON_ANALISE" scripts/analyze_comparison_v43.py report --cohort "$COHORT_V43" \
  --output "$COHORT_V43/analysis-v43"
```

O relatório automático marca a revisão humana como pendente. Após consolidar os dois formulários, gere outro relatório com a amostra humana em seção própria. A análise conserva os rótulos automáticos do lote integral.

```sh
"$PYTHON_ANALISE" scripts/analyze_comparison_v43.py report --cohort "$COHORT_V43" \
  --human-report "$COHORT_V43/human-scores.json" \
  --output "$COHORT_V43/analysis-v43-with-human"
```

O bootstrap pareado reamostra cenários inteiros e mantém as repetições agrupadas. Os contrastes principais usam os pares completos e mostram a cobertura e os limites para todos os pares planejados quando houver dados desconhecidos. Os p-valores automáticos vêm de inversões de sinal das diferenças por cenário, sob a hipótese de invariância a essas inversões. Holm cobre os três contrastes. Os intervalos percentis de 95% são marginais. Os contrastes da amostra humana são descritivos.

Os CSVs preservam denominadores e distribuições ordinais. A rechecagem do mesmo julgador mede estabilidade no subconjunto congelado, incluindo mudanças no composto anterior e nas dimensões da rubrica. A latência do núcleo e a latência do coletor são resumidas com p50 e p95 das tentativas medidas e quartis das medianas por cenário. São medições descritivas sob carga mista na configuração congelada. O custo estimado por fase e arquitetura usa requisições físicas e as tarifas geográficas de geração e julgamento. Cache, uso parcial ou ausência de observação são explicitados. API, piloto e calibração têm escopo próprio.

## Conferência histórica

O comando abaixo lê os 600 registros públicos v4.2 e reproduz os três contrastes publicados do desfecho composto. A saída é um novo arquivo local. Os protocolos, cenários e desfechos históricos permanecem identificados separadamente.

```sh
"$PYTHON_ANALISE" scripts/analyze_comparison_v43.py audit-v42 \
  --source research-data/results/agents-as-tools-v42 \
  --output "$AUDITORIA_V42_JSON"
```
