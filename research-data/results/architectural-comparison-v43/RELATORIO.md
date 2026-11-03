# Comparação v4.3

## Resultado automático provisório

Foram analisadas 360 unidades em 40 cenários, com 3 repetições por condição.
O desfecho primário avalia requisitos essenciais, recomendação profissional obrigatória e violações críticas no conteúdo da resposta.
Conclusão técnica, contrato arquitetural, consulta obrigatória e sucesso composto são medidas separadas.

| Condição | Conteúdo aprovado | Conhecido | Desconhecido | Planejado |
|---|---:|---:|---:|---:|
| centralized_orchestration | 99 | 119 | 1 | 120 |
| structured_workflow | 101 | 119 | 1 | 120 |
| decentralized_swarm | 90 | 120 | 0 | 120 |

| A | B | Cenários completos | B − A (pp) | IC95% (pp) | p Holm | Limites com desconhecidos (pp) |
|---|---|---:|---:|---:|---:|---:|
| centralized_orchestration | structured_workflow | 38/40 | 1.75 | 0.00 a 5.26 | 1.0000 | 0.83 a 2.50 |
| centralized_orchestration | decentralized_swarm | 39/40 | -8.55 | -18.80 a 0.00 | 0.2500 | -8.33 a -7.50 |
| structured_workflow | decentralized_swarm | 39/40 | -10.26 | -20.51 a -2.56 | 0.1875 | -10.00 a -9.17 |

As comparações agrupam as repetições dentro de cada cenário. Os intervalos percentis são marginais e condicionais à amostra.
A permutação inverte os sinais das diferenças por cenário e usa a média das diferenças como estatística. O teste pressupõe invariância conjunta a essas inversões sob a hipótese nula. Holm corrige os três contrastes primários.
Os CSVs incluem os desfechos secundários e as distribuições ordinais por dimensão. As comparações por estrato são descritivas.

## Tempo e recursos do lote

Geração em carga mista com até 24 processos por onda. As latências p50 e p95 usam tentativas com tempo medido. O arquivo de medições também inclui quartis das medianas de cenários completos.

| Condição | Medida | Tentativas medidas | p50 (ms) | p95 (ms) |
|---|---|---:|---:|---:|
| centralized_orchestration | núcleo | 120/120 | 8231.67 | 14625.73 |
| structured_workflow | núcleo | 120/120 | 9439.50 | 14504.37 |
| decentralized_swarm | núcleo | 120/120 | 5252.98 | 8613.33 |
| centralized_orchestration | coletor | 120/120 | 14324.17 | 20773.64 |
| structured_workflow | coletor | 120/120 | 15343.91 | 20617.00 |
| decentralized_swarm | coletor | 120/120 | 11095.83 | 15189.08 |

| Fase | Condição | Requisições com uso | Tokens conhecidos | Estimativa integral (USD) |
|---|---|---:|---:|---:|
| Geração | centralized_orchestration | 504/504 | 803640 | 1.2308 |
| Geração | structured_workflow | 507/507 | 613199 | 1.0384 |
| Geração | decentralized_swarm | 255/255 | 430204 | 0.6596 |
| Julgamento | centralized_orchestration | 121/121 | 830000 | 3.9775 |
| Julgamento | structured_workflow | 120/120 | 824115 | 3.9484 |
| Julgamento | decentralized_swarm | 120/120 | 822494 | 3.9567 |
| Rechecagem | centralized_orchestration | 5/5 | 33844 | 0.1597 |
| Rechecagem | structured_workflow | 5/5 | 34272 | 0.1628 |
| Rechecagem | decentralized_swarm | 5/5 | 33972 | 0.1658 |

As estimativas usam as tarifas geográficas padrão e os eventos de requisições físicas. O CSV separa parcelas conhecidas e totais indisponíveis.
A contagem de transferências usa um ID por solicitação de handoff. O CSV de coordenação mostra as mensagens vinculadas separadamente.

## Estabilidade do julgador

| Condição | Pares válidos no schema | Pares com composto conhecido | Mudanças |
|---|---:|---:|---:|
| centralized_orchestration | 5/5 | 5 | 0 |
| structured_workflow | 5/5 | 5 | 0 |
| decentralized_swarm | 5/5 | 5 | 0 |

A rechecagem repete o julgador no subconjunto congelado. A tabela usa o desfecho composto anterior. O CSV inclui mudanças por dimensão e divergências nas violações críticas.

## Revisão humana da amostra cega

Pendente de revisão humana independente nas 30 unidades pré-selecionadas.

O benchmark emprega referências técnicas controladas. A validade clínica e a generalização para atendimento real permanecem em aberto.
