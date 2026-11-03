# Amostra sintética v4.3

O lote `main-360-02` usa a matriz `synthetic-new-v43.1`, com 40 cenários novos escritos para as capacidades controladas do benchmark. Os seis cenários do piloto de engenharia pertencem a uma coorte separada. A redação das entradas e dos critérios da matriz foi concluída antes da geração principal. A validação encontrou 46 entradas distintas nas duas coortes e zero correspondências exatas com as 53 entradas anteriores identificadas.

O inventário histórico encontrou 105 episódios em 79 grupos conhecidos após aplicar as exclusões da partição de teste e dos grupos já usados. Os dois episódios de teste aprovados na base de candidatos pertenciam ao piloto anterior. A matriz nova foi escrita a partir das categorias e dos contratos das ferramentas. Seus 40 registros têm origem `synthetic-new-authored` e referências técnicas derivadas dos cenários e das fontes controladas. Os conteúdos e as referências por caso permanecem no pacote restrito.

## Composição

Cada categoria tem três cenários simples, três intermediários e dois complexos. Simples indica uma demanda focal. Intermediário envolve contexto, desambiguação ou uma limitação da fonte. Complexo envolve requisitos independentes, contexto acumulado ou combinação de demandas e limites. A categoria agrupa a demanda principal e pode incluir consultas a fontes de outras categorias.

| Categoria | Cenários | Simples | Intermediários | Complexos | FAQ obrigatória | Estoque obrigatório | Metadados obrigatórios |
|---|---:|---:|---:|---:|---:|---:|---:|
| FAQ | 8 | 3 | 3 | 2 | 10 | 0 | 0 |
| Estoque | 8 | 3 | 3 | 2 | 0 | 10 | 0 |
| Anexos | 8 | 3 | 3 | 2 | 1 | 2 | 3 |
| Encaminhamento profissional | 8 | 3 | 3 | 2 | 0 | 3 | 1 |
| Continuidade | 8 | 3 | 3 | 2 | 4 | 4 | 0 |
| Total | 40 | 15 | 15 | 10 | 15 | 19 | 4 |

Dez cenários têm zero consulta de domínio obrigatória, 22 têm uma e oito têm duas. Há cinco consultas opcionais a metadados. Essas contagens descrevem requisitos do gabarito. A execução de especialistas e a comprovação de consultas são medidas nas trajetórias.

Nove cenários têm histórico. Nove trazem anexos na entrada atual, representados por 12 descritores fictícios, seis de imagem, cinco de PDF e um de áudio. O protocolo exige o especialista de anexos nesses nove casos, e o gabarito especifica em quais casos conferir os metadados faz parte da tarefa. O gatilho comum de encaminhamento coincide com o indicador esperado e com a presença do critério de recomendação explícita nos 40 cenários. São oito positivos e 32 negativos. O requisito de transferência efetiva é falso em todos os casos.

## Pareamento e revisão humana

O manifesto e a ordem exportada concordam nas 360 unidades, 120 por condição. As três arquiteturas recebem o mesmo caso em cada combinação de cenário e repetição. As 120 tripletas incluem 20 ocorrências de cada uma das seis permutações. O despacho prevê 15 ondas de 24 unidades, oito por arquitetura em cada onda. A análise agrupa as três repetições de cada arquitetura por cenário.

O seletor humano ordena os estratos e os identificadores de cenário, sorteia dois cenários distintos por estrato com a semente `20261011` e sorteia uma repetição comum às três arquiteturas para cada cenário selecionado. A pré-seleção reprodutível cobre 10 cenários e 30 unidades, 10 por arquitetura. Inclui cinco cenários simples, três intermediários e dois complexos. Em 2 de novembro de 2026, o plano foi congelado às 22:38:51,192796 em São Paulo. O primeiro lançamento registrado ocorreu às 22:38:51,936455.

O plano prevê duas avaliações independentes por unidade, com identificadores opacos e ordenação própria para cada revisor. As fichas incluem contexto, resposta e referência técnica. A seleção e o plano preservam indisponibilidades e desacordos. O consenso exige dois rótulos conhecidos e iguais. A pré-seleção documenta a amostra planejada, enquanto o preenchimento humano constitui uma etapa separada. [Plano de análise](analysis-plan.json) · [Seletor e verificador](../../scripts/human_review_v43.py)

## Evidências para reprodução

A auditoria comparou os três assets do manifesto com os arquivos de origem e as cópias congeladas. O catálogo contém os mesmos 40 casos e hashes individuais do manifesto. O plano humano tem o hash do seletor usado, que reproduz a seleção congelada. A validação local da preparação conferiu os contratos das fontes, a igualdade da entrada normalizada entre condições e a separação entre contexto e gabarito. O pacote restrito conserva o catálogo, as testemunhas e os utilitários `build_fixtures.py` e `audit_fixtures.py`.

| Artefato | SHA-256 |
|---|---|
| Catálogo `main-40.json` | `efa4e237e90f07a07ef9b27da2b49742fe6abae481de8e3f0f73994f62680d28` |
| Casos em serialização canônica do manifesto | `cceff3986ca55c1f6343f17ae9ec48db96dffd80ca3fee6ca7c56c5c738cd79c` |
| Testemunhas dos contratos | `866e3ee15adcc668f4134a4d10f44984b3e7123d342b76eb1dc1e1d011d35e1b` |
| Validação local das entradas | `8a9e3a020ebd7d6c0ce2fa17f9f31059e4496892ff424b4610e665a90cc6e207` |
| Manifesto efetivo do lote | `3599fb05ce1a72bd8ff2631fcc04252e37e3d234c28f71638b4da63039333853` |
| Ordem de execução CSV | `fc98d3c29f54c69421d5cadca11ff24fca62af6a3807977d4983db9fc3cdab2d` |
| Plano de análise em JSON canônico | `c8853d44122bbc636e8abc2ffea786b0fea6ff23dde640296bb2083637930079` |
| Pré-seleção para revisão humana | `5d28bb6bb0e9f55a33c97124da8f5c380490bfcb52d2f4946a76ac321eddccea` |
| Código do seletor humano | `6ef60b140349a67757aa749e03057fa10d190ce87d80864917e1bd638cc1dafd` |

## Limites

As quotas são intencionais e equilibram cobertura, com frequência fixada pelo desenho. Os resultados descrevem os cenários sintéticos e as implementações testadas. As referências de estoque, metadados e encaminhamento medem o cumprimento de contratos técnicos. A comparação histórica com v4.2 incorpora mudanças de amostra, implementação e desfecho e deve permanecer descritiva. A amostra humana tem caráter descritivo, e o estilo do texto pode dar pistas sobre sua origem mesmo com os identificadores ocultados. [Protocolo v4.3](README.md)
