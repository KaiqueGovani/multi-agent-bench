# Eficiência de sucesso por consumo de tokens — v4.4

Figura complementar derivada do mesmo lote das figuras de sucesso da tarefa
(63,0%, 60,5% e 57,0%) e das distribuições de tokens. Não altera os resultados,
critérios ou análises congelados. É uma análise descritiva posterior à coleta.

## Reprodução

Requer Python e Matplotlib. A partir da raiz do repositório:

```sh
python3 scripts/render_success_token_efficiency.py
```

O destino padrão é `var/success-token-efficiency-v44/`, ignorado pelo Git.
`--output-dir CAMINHO` escolhe outro destino. O script produz PNG (300 dpi),
SVG, CSV, proveniência JSON e uma legenda em texto, sem alterar as fontes.

As entradas públicas são `units.csv` e `architecture-summary.csv` em
`research-data/results/architectural-comparison-v44/`. O script verifica os
600 pares únicos de cenário/arquitetura/repetição, as 200 tentativas por
arquitetura, a completude dos tokens, os desfechos conhecidos e a reconciliação
dos totais com o resumo congelado.

## Definição

**Sucessos por milhão de tokens = sucessos observados ÷ tokens totais × 1.000.000.**

O numerador usa `task_success`, não apenas conclusão técnica ou sucesso de
conteúdo. O denominador usa `total_tokens` de todas as tentativas, inclusive
as que não cumpriram a tarefa. Considera entrada e saída dos agentes de
geração; exclui o julgador automático. Não seleciona somente tentativas bem
sucedidas, pois isso esconderia o consumo das demais.

É equivalente à taxa de sucesso dividida pela **média** de tokens por tentativa.
Não se deve dividir a taxa global pela mediana do boxplot e apresentar o
resultado como rendimento agregado: a figura original resume medianas por
cenário, e essa divisão produziria outro índice descritivo.

| Configuração | Sucessos / tentativas | Tokens de geração | Sucessos / milhão de tokens | Tokens / sucesso observado |
|---|---:|---:|---:|---:|
| Centralizada | 126 / 200 | 1.545.748 | 81,5139 | 12.267,84 |
| Workflow | 121 / 200 | 1.274.425 | 94,9448 | 10.532,44 |
| Swarm | 114 / 200 | 1.482.278 | 76,9087 | 13.002,44 |

## Leitura permitida

Neste lote, o Workflow teve 2,5 pontos percentuais menos sucesso que a
Centralizada, com 16,48% mais sucessos por milhão de tokens — equivalente a
14,15% menos tokens por sucesso observado. O Swarm teve 5,65% menos eficiência
em tokens que a Centralizada. Portanto, o indicador favorece o Workflow nessa
troca observada, mas não favorece o Swarm.

Não constitui teste de superioridade estatística, previsão de rendimento em
produção, validação clínica ou demonstração de que uma perda de sucesso é
aceitável. As 200 tentativas por configuração vêm de 40 cenários com cinco
repetições; não são 200 cenários independentes. O sucesso é o definido pelo
instrumento automático congelado, com revisão humana ainda pendente.

Tokens também não são dólares: entrada e saída têm pesos financeiros
diferentes. Pelas estimativas monetárias já congeladas no lote, o custo de
geração por sucesso é US$ 0,01938221 / US$ 0,01826866 / US$ 0,02182803,
respectivamente. A redução estimada do Workflow por sucesso é 5,75%,
diferente do ganho de eficiência em tokens. Não foram consultados preços
atuais nem incluído o custo do julgador nessa comparação.
