# Comparação v4.4

Este protocolo executa uma matriz nova de 40 cenários originais derivados do WhatsApp, cinco repetições e três configurações. A identidade dos cenários e dos gabaritos é conferida contra o manifesto privado v4.2. O desenho mantém fontes controladas, modelo, parâmetros, SDK, semente de ordenação e instrumento de julgamento. O cenário é a unidade pareada. Os resultados v4.1, v4.2 e v4.3 são históricos.

## Configurações

- **Centralizada.** Um supervisor escolhe ferramentas que executam especialistas Strands de FAQ, estoque e anexos e conserva a autoria da resposta. O executor verifica o conjunto de ferramentas anunciado em cada turno antes de executar uma chamada. O primeiro turno exige um especialista. Um descritor de anexo exige a conclusão real do especialista correspondente. As demais ferramentas ficam disponíveis em um turno posterior, após cumprir a obrigação. Chamadas fora do escopo geram um evento de rejeição e um erro de ferramenta para o supervisor. O contrato verifica o resultado real do especialista e a requisição física concluída antes de aceitar a resposta.
- **Workflow.** O roteador, a execução dos especialistas e a síntese seguem o fluxo v4.2.
- **Swarm.** O coordenador inicial, as delegações entre especialistas e o sintetizador final seguem o fluxo v4.2.

Os limites técnicos são 20 requisições ao modelo, 20 chamadas de domínio e 180 segundos por tentativa. O supervisor pode executar até seis chamadas de especialista, e o swarm mantém o teto de seis delegações. Os registros distinguem rejeição antes da execução, chamadas realizadas, respostas dos filhos e requisições físicas. A reconciliação de tokens usa os IDs das requisições físicas registradas.

## Ordem da coleta

O piloto usa seis entradas sintéticas separadas e uma tentativa em cada configuração. A liberação exige rastreamento íntegro, delegações físicas e conformidade com o contrato, independentemente da qualidade das respostas. O lote principal contém somente 600 primeiras tentativas novas, em subprocessos isolados, admitidos em ondas de até 48 processos. Cada onda contém tripletas completas, com a mesma quantidade de tentativas por configuração, e termina antes da próxima. O sorteio contrabalanceado determina a ordem planejada de admissão. O julgamento cego usa até 48 processos depois da geração, com um proprietário por resposta e o instrumento congelado. O teste de capacidade concluiu 48 requisições simultâneas por modelo.

O autor solicitou a concorrência depois de iniciada a primeira coleta sequencial. Essa coleta parou após 54 tentativas, antes de qualquer julgamento. O lote paralelo começa com 600 tentativas novas e tem plano próprio congelado antes da geração. As latências descrevem a carga mista medida; a comparação direta com latências sequenciais exige distinguir os dois desenhos. As 15 rechecagens avaliam a estabilidade do mesmo juiz.

O desfecho primário preserva o sucesso de tarefa composto da v4.2. As tabelas mostram separadamente conclusão técnica, contrato, conteúdo e consulta obrigatória. O [plano pré-coleta](analysis-plan.json) registra a análise pareada e os critérios de dados ausentes. O [inventário metodológico](DATASET.md) descreve a origem e os limites da amostra. Os cadernos da v4.3 correspondem a outro experimento. As avaliações deste lote são automáticas, com referências técnicas e sem validação clínica independente.

## Abrir os resultados publicados

A partir da raiz do checkout, instale o frontend com `npm ci --prefix apps/web` e execute `make research-results`. Abra [a comparação v4.4](http://127.0.0.1:3000/research/comparison-v44) para explorar as tabelas e as figuras. A visualização lê os arquivos versionados da [coleta publicada](../../research-data/results/architectural-comparison-v44/README.md).

## Rodar o piloto sintético

Com o ambiente do runtime instalado por `uv sync --all-extras` em `apps/agent-runtime` e a credencial do Bedrock configurada localmente, use os comandos abaixo a partir da raiz. Escolha diretórios de saída novos. A calibração usa as referências sintéticas versionadas.

```sh
export AWS_REGION=us-west-2
runner=apps/agent-runtime/.venv/bin/python
calibration=var/reports/v44-local/judge-calibration

"$runner" scripts/judge_automated_pilots.py "$calibration" --calibrate
"$runner" scripts/run_research_pilot.py --protocol architectural-comparison-v4.4 \
  --cases experiments/corrected-comparison-v4.2/pilot-six.json --repetitions 1 \
  --generation-workers 3 --calibration "$calibration" \
  --analysis-plan experiments/architectural-comparison-v44/analysis-plan.json \
  --output var/reports/v44-local/pilot
```

Para coletar novamente as 600 unidades, o responsável pela pesquisa usa o catálogo, o manifesto histórico e o pacote de calibração restritos. O coletor congela os insumos com `--plan-only`. `scripts/validate_comparison_v44_pilot.py` libera o manifesto principal após o piloto. Em seguida, o coletor retoma com `--resume`, `scripts/parallel_judge.py` despacha o julgamento e as rechecagens, e `scripts/analyze_automated_pilots.py` consolida a evidência. `scripts/analyze_comparison_v44.py` exporta os resultados sanitizados e aceita `--writer-zip` para empacotar o relatório.
