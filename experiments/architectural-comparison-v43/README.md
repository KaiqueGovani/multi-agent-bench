# Comparação de coordenação v4.3

A unidade da análise é o cenário. O desenho mantém as três condições na mesma combinação de cenário e repetição, usa ordem sorteada em blocos e preserva as primeiras tentativas. A v4.2 permanece como diagnóstico histórico com protocolo e cenários próprios.

## Contrato e condições

Toda resposta final requer pelo menos um especialista executado com requisição física concluída. A presença de descritor de anexo na mensagem atual exige a execução do especialista de anexos antes da resposta em todas as condições. A comprovação de consulta a uma fonte específica permanece como uma medida separada. O contexto de entrada, a política de domínio, as fontes, o modelo, os parâmetros e os limites globais são compartilhados.

- Centralizada. O supervisor escolhe um especialista como ferramenta no primeiro turno, ou usa o especialista de anexos quando o contrato exige. Pode solicitar outras consultas e mantém a autoria da resposta.
- Workflow. Um roteador seleciona etapas, os especialistas executam as consultas e um sintetizador encerra.
- Descentralizada. Um especialista recebe a entrada por uma regra fixa de ingresso. Anexos entram pelo especialista de anexos e demais casos entram pelo FAQ. O agente responsável decide se responde ou transfere a autoridade a um par. O responsável ao final encerra.

## Execução e amostra

O piloto de engenharia testa as três condições, anexos, encaminhamento e a transferência real entre especialistas. A matriz principal usa 40 cenários sintéticos inéditos, oito por estrato, com três repetições por condição e 360 tentativas. As diferenças são analisadas entre os 40 pares de cenários. O tamanho foi escolhido para manter a curadoria auditável e a coleta curta. Como referência de planejamento, os desvios dos contrastes por cenário no desfecho composto v4.2 implicariam meias-larguras marginais de aproximadamente 6 a 19 pontos percentuais com 40 cenários. Essa faixa é ilustrativa, pois o endpoint primário e a configuração mudaram. A precisão efetiva será mostrada pelos intervalos do novo lote. A amostra intencional favorece cobertura de categorias e fornece evidência sobre os cenários simulados.

As unidades são executadas em processos isolados. Cada onda contém tripletas completas de cenário e repetição, com igual número de tentativas por arquitetura. O limite de concorrência é congelado no manifesto a partir do teste de capacidade. Latência de núcleo e latência do coletor representam o ambiente concorrente testado. As requisições de julgamento usam um despacho cego separado, com um proprietário por resposta.

O plano pré-coleta em [analysis-plan.json](analysis-plan.json) define conteúdo e segurança da resposta como desfecho primário, com conformidade, consultas e sucesso composto separados. A comparação automatizada fica provisória até a avaliação independente da amostra humana pré-selecionada. As referências são técnicas e os cenários usam fontes controladas. A conclusão se restringe ao benchmark.

## Reproduzir a coleta

O arquivo de cenários e o diretório da execução ficam em armazenamento restrito. Os comandos abaixo usam o ambiente virtual do runtime com o SDK 1.37.0. Configure a credencial Bedrock por variável de ambiente e use a região `us-west-2` também no julgador.

```sh
runtime=apps/agent-runtime/.venv/bin/python
export AWS_REGION=us-west-2
"$runtime" scripts/run_research_pilot.py --protocol architectural-comparison-v4.3 \
  --cases "$CASES_V43" --output "$COHORT_V43" --repetitions 3 \
  --generation-workers 24 --analysis-plan experiments/architectural-comparison-v43/analysis-plan.json \
  --plan-only
"$runtime" scripts/human_review_v43.py plan --cohort "$COHORT_V43"
"$runtime" scripts/run_research_pilot.py --output "$COHORT_V43" --resume --continue-after-failure
"$runtime" scripts/parallel_judge.py "$COHORT_V43" --phase both --workers 24 --allow-inference
"$runtime" scripts/analyze_automated_pilots.py "$COHORT_V43" \
  --calibration var/reports/automated-pilots-v5/calibration-v5.2
```

Os hashes do código executado e dos cenários ficam no manifesto privado. O dispatcher preserva os resultados terminais ao retomar a geração. Uma falha de capacidade ou autorização do provedor interrompe o despacho entre ondas completas. Os dois pacotes de avaliação humana devem ser entregues separadamente, preservando o cegamento. A análise automatizada e as rechecagens do mesmo juiz têm escopos próprios.
