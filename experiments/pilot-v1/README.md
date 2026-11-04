> Documento histórico do piloto v3. Os comandos correspondem ao código arquivado daquela rodada. O código atual executa o protocolo v4; consulte [pilotos automatizados](../pilots-v4/README.md). Não combinar as rodadas.

O catálogo individual do piloto fica no acervo restrito da pesquisa.

# Piloto de comparação arquitetural — protocolo v3

Este é um piloto técnico com referências provisórias dos autores. Os farmacêuticos ainda não validaram os casos, os critérios, a política de encaminhamento ou as notas. Não usar o piloto como resultado definitivo do TCC.

## Condições comparadas

As três condições usam o mesmo modelo e região efetivos, temperatura explícita 0, limite explícito de tokens por resposta, ferramentas e fontes controladas, janela de até oito mensagens e política comum de encaminhamento. Os prompts completos por papel e seus hashes constam no manifesto. Não se usa top_p junto de temperatura; essa omissão é registrada, assim como stop_sequences vazio e streaming desabilitado. Retries automáticos do SDK/cliente estão desabilitados.

- Centralizada: um supervisor com as três ferramentas de domínio e decisão de coleta.
- Workflow: roteador com saída estruturada, especialistas sequenciais para as fontes selecionadas e síntese final.
- Swarm: coordenador inicial com plano de rotas estruturado e validado, execução obrigatória desse plano, especialistas com delegação entre pares, limite de transferências, bloqueio de ciclos na cadeia ativa e síntese final obrigatória. Não é um swarm sem coordenador.

Quantidade de chamadas, seleção de fontes e circulação de contexto decorrem da arquitetura. A mesma regra de encaminhamento, provisória e baseada na entrada, vale para todas. O cumprimento do encaminhamento no texto é avaliado separadamente da flag comum: a flag isolada não demonstra melhor capacidade de uma arquitetura. Essa regra não é um classificador clínico validado.

## Casos iniciais

Sete casos são reconstruções de demandas observadas nos sete prefixos liberados do SQLite de piloto. Textos foram abreviados e reconstruídos, sem nomes ou mensagens futuras. Três são controles sintéticos. Isso não é replay literal nem amostra representativa. Categorias e dificuldades são provisórias, sem distribuição equilibrada da matriz definitiva.

| Caso | Categoria | Dificuldade | Origem | Encaminhamento provisório |
|---|---|---|---|---|
| delivery_today | faq | low | reconstructed-whatsapp | não |
| finish_order_unknown_product | continuity | high | reconstructed-whatsapp | não |
| quetiapine_availability | stock | medium | reconstructed-whatsapp | não |
| veterinary_failed_treatment | professional_review | high | reconstructed-whatsapp | sim |
| missing_prescription | professional_review | high | reconstructed-whatsapp | sim |
| order_tracking | continuity | medium | reconstructed-whatsapp | não |
| generic_price | stock | medium | reconstructed-whatsapp | não |
| opening_hours | faq | low | synthetic-control | não |
| stock_known | stock | low | synthetic-control | não |
| attachment_unreadable | attachments | medium | synthetic-control | não |

O catálogo define critérios, não respostas históricas como gabaritos. Estoque e FAQ vêm da POC controlada, não dos registros reais da farmácia. Não há preços nem consulta de pedidos; produto fora do catálogo tem disponibilidade desconhecida. O caso de anexo tem somente descritores sintéticos, não bytes de imagem: avalia reconhecimento de limites da ferramenta, não qualidade de OCR/visão.

## Executor e métricas

O novo executor usa o núcleo RuntimeExecutor/ExecutionContext com o protocolo explícito `architectural-comparison-v3`. Também é selecionável no fluxo da API mediante esse metadado, mas o piloto roda diretamente, sem banco/HTTP. Seus tempos representam execução do núcleo, incluindo instrumentação local, e não latência ponta a ponta do atendimento.

O executor embaralha blocos cenário×repetição e a ordem das três arquiteturas dentro de cada bloco, com seed preservada. Uma execução ocorre por vez, com ferramentas sequenciais. O planejamento padrão é 10×3×1 = 30 unidades. Uma repetição basta para diagnóstico de engenharia; não estima estabilidade, efeito ou significância. Não há contrabalanceamento exato garantido.

O manifesto e a cópia code-snapshot preservam casos, ordem, código efetivo (incluindo arquivos não commitados), SDK, prompts e configurações sem credenciais. A ordem completa é salva antes das chamadas. Cada tentativa tem identificador e diretório próprios; eventos são gravados incrementalmente e respostas são integrais. Não há fallback para mock nem transformação de tokens ausentes em zero. Uso é da última invocação de cada agente, evitando somar novamente métricas acumuladas em agentes reutilizados.

Métricas: duração da execução, duração por invocação, tokens, requisições ao modelo (ciclos SDK), invocações de agente, ferramentas de domínio, ferramentas de coordenação/saída estruturada, erros e handoffs. Não somar tempos de agentes aninhados como duração total; não interpretar chamadas a agentes como número de requisições LLM. Etapas de workflow não são comparáveis diretamente com loops de swarm. Consumo incompleto/falha preserva NULL na medição principal. Custo monetário requer tarifa verificada e análise posterior; não é inferido por preço inventado.

Cada tentativa tem limite total externo em processo separado, incluindo inicialização, e é encerrada ao atingir esse limite. O tempo principal de uma execução concluída começa dentro do núcleo; o tempo de encerramento externo é explicitado como timeout/interrupção. Falha interrompe o lote por padrão. Retomada mantém tentativas terminais, inclusive falhas, e segue unidades pendentes sem repetir as anteriores. Tentativa inconclusa/lock deixado por interrupção abrupta exige inspeção do processo antes de remover o lock ou autorizar substituição. Não há substituição automática de falhas.

## Execução

No repositório, com dependências do runtime instaladas e credencial válida em apps/agent-runtime/.env:

```sh
make research-pilot-plan PILOT_ARGS="--output /caminho/absoluto/plano"
make research-pilot PILOT_ARGS="--output /caminho/absoluto/piloto"
make research-pilot PILOT_ARGS="--output /caminho/absoluto/piloto --resume"
make research-pilot-judge PILOT_OUTPUT=/caminho/absoluto/piloto
```

Planejar com --plan-only e depois executar naquele mesmo diretório requer --resume. Modificações no código congelado exigem um experimento novo. `--case` seleciona casos para verificação menor; --architecture restringe uma rodada de verificação a uma condição. Essa rodada não deve ser combinada com a comparação anterior como uma amostra única. `--model`, `--region`, `--timeout`, `--max-tokens`, `--repetitions` e `--seed` são controles explícitos. Os benchmarks legados continuam sendo ferramentas de integração da POC; não usar seus CSVs como coleta deste protocolo.

## Juiz automático e dois farmacêuticos

O avaliador usa as respostas completas sem arquitetura, eventos, contagens, tempos ou metadados que revelem a condição. Cada avaliação recebe contexto, critérios provisórios, fontes controladas e rubrica de cinco dimensões 1–5: correção, completude, clareza, contexto e segurança. As notas e justificativas ficam separadas, com encaminhamento, erro crítico e problemas de referência em campos adicionais. Notas inválidas ou falha do juiz não viram zero e não são substituídas automaticamente.

Modelo, região, parâmetros e prompt do juiz são registrados. O padrão usa o modelo disponível, podendo ser alterado por --model; quando igual ao modelo avaliado, há risco de preferência pelo próprio modelo, registrado no manifesto do juiz. Avaliações do piloto ainda não foram calibradas com humanos. Não interpretar suas notas como precisão clínica validada.

O exportador gera respostas em ordem embaralhada e formulário para ambos os farmacêuticos avaliarem independentemente a mesma amostra. Neste piloto de uma repetição, podem avaliar todas as 30 respostas; na matriz definitiva deve-se congelar a amostra antes de olhar resultados. Não fornecer blind-mapping.json, runs.csv ou eventos aos avaliadores. Concordância deve ser calculada antes de consenso/adjudicação.

Preencher notas inteiras 1–5, ou NA com justificativa; referral_adequacy = adequate/inadequate/not_assessable e critical_error = true/false. Importação valida IDs, faixa e duplicações, preservando avaliações anteriores:

```sh
cd apps/agent-runtime
uv run python ../../scripts/evaluate_research_pilot.py /caminho/absoluto/piloto --import-human /caminho/absoluto/notas.csv
```

O relatório de concordância inclui número de pares, concordância exata, diferença absoluta e kappa de Cohen com pesos quadráticos por dimensão. Sem pares ou variabilidade suficiente, métricas indefinidas são NULL. Essas estatísticas são descritivas do piloto e não atestam validade clínica; intervalos de confiança/análise de efeito pertencem ao protocolo definitivo.

## Critérios para avançar

Confirmar chamadas reais nas três condições, ausência de fallback, contrato estruturado de roteamento, pareamento de ferramentas, medição completa e resposta integral. Revisar qualitativamente resultados e falhas. Depois validar casos/rubrica/encaminhamento com farmacêuticos, corrigir instrumentos, ampliar catálogo e congelar protocolo definitivo. Validar separadamente a integração API/banco e a janela de contexto; ela não está demonstrada pelo piloto direto.

## Revisão após o primeiro piloto

O protocolo v1 concluiu 23 de 30 tentativas; o swarm encerrou sete casos sem delegação e sem evidências. As tentativas e o código anterior foram preservados. A revisão v2 torna explícito no papel do coordenador que encaminhamento e desconhecimento de preço/estoque não dispensam delegação. Essa é uma instrução de coordenação, mantendo regras de domínio, encaminhamento, fontes e parâmetros. Sua verificação é uma rodada separada, não substituição das sete falhas. Casos usados nestes pilotos devem ficar fora da avaliação definitiva, inclusive quando estavam originalmente em uma partição denominada test: já foram vistos na preparação e revisão dos instrumentos.

A verificação v2 do swarm terminou com sete conclusões e três falhas em dez casos; reforço textual não garantiu o fluxo. A revisão v3 usa planejamento inicial estruturado e validado, executado pelo controlador da arquitetura, mantendo delegação livre entre especialistas. É um swarm com bootstrap coordenado, não descentralização integral. Handoffs originados pelo plano têm invocationOrigin=architecture_plan; outros são solicitados pelos especialistas via LLM. Ambas as origens são preservadas. Erros intermediários de ferramenta são contados separadamente do sucesso terminal: se houver resposta final, sua qualidade será avaliada, sem declarar que o erro foi resolvido. Falhas de modelo, plano inválido, transferência inicial não concluída ou ausência de resposta continuam falhas técnicas. As versões anteriores tinham critério mais estrito para qualquer erro de ferramenta e não devem ser combinadas com v3.

A seed controla a ordem experimental, não a aleatoriedade interna do provedor. A comparação definitiva precisa de repetições e análise de incerteza. Para resumir uma rodada concluída: `uv run python ../../scripts/summarize_research_pilot.py /caminho/absoluto/piloto` a partir de apps/agent-runtime.

Referência para vieses do juiz automático: [Zheng et al., Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685).
