# Protocolo experimental do MAB

Status: rascunho metodológico atualizado em 2026-09-03; ainda não congelado. A fonte autoral da revisão de base é o documento “4 METODOLOGIA — versão revisada”, fornecido por Kaique Govani em 25 de agosto de 2026. O procedimento de ordenação foi formalizado em 3 de setembro de 2026 para substituir a indicação anterior, não reproduzível, de alternância ou randomização.

## 1. Objetivo

Comparar orquestração centralizada, *workflow* estruturado e coordenação descentralizada por *handoffs* sob condições equivalentes, utilizando o atendimento em farmácias como estudo de caso instrumental. O protocolo mede diferenças de eficiência operacional, custo de coordenação, qualidade e segurança sem presumir qual arquitetura será superior.

Não será incluído um agente único como *baseline*, pois o objeto do estudo é a comparação entre estratégias de coordenação multiagente.

## 2. Unidade experimental

A unidade experimental é uma execução de um cenário por uma arquitetura. Cada execução deverá registrar versão do código, arquitetura, cenário, repetição, modelo, parâmetros, ferramentas, limites, ordem e condições relevantes do ambiente.

As repetições da mesma combinação cenário-arquitetura serão preservadas individualmente, mas serão agregadas por cenário e arquitetura na comparação estatística principal para evitar tratá-las como observações completamente independentes.

## 3. Arquiteturas

- `centralized_orchestration`: um supervisor concentra decisões de roteamento e uso de ferramentas.
- `structured_workflow`: o processamento ocorre por etapas previamente definidas.
- `decentralized_swarm`: agentes especializados transferem diretamente a responsabilidade por meio de *handoffs*.

## 4. Origem, construção e estratificação dos cenários

Os cenários serão derivados de conversas reais de atendimento realizadas por WhatsApp, coletadas e tratadas em ambiente privado. Nenhuma conversa, transcrição, mídia, identificador ou dado de saúde individual será versionado no repositório público.

A anonimização removerá ou substituirá nomes, telefones, endereços, documentos, identificadores e informações pessoais desnecessárias. Quando possível, serão preservadas abreviações, informalidade, erros ortográficos e demais características linguísticas relevantes, sem conservar formulação que permita reidentificação.

Cada cenário deverá conter, no mínimo:

- identificador único;
- mensagens e contexto necessários;
- estrato experimental;
- nível de dificuldade;
- intenção principal;
- ferramenta ou evidência esperada, quando aplicável;
- indicação de necessidade de revisão profissional;
- elementos esperados de uma resposta adequada; e
- comportamentos ou informações proibidos.

O conjunto terá 40 cenários, distribuídos em cinco estratos de oito cenários: FAQ, estoque, anexos, revisão profissional e continuidade de contexto. Em cada estrato serão selecionados três cenários de menor complexidade, três intermediários e dois de maior complexidade.

Os estratos são dimensões do desenho experimental e podem se sobrepor. Um cenário classificado como anexo, por exemplo, também poderá exigir continuidade ou revisão profissional.

A unidade de segmentação dos históricos em episódios continua pendente na OQ-004 e será definida após a coleta exploratória. A seleção e a classificação definitivas ocorrerão antes de qualquer execução comparativa, evitando influência dos resultados na composição do conjunto.

Os oito cenários do estrato de revisão profissional e seus gabaritos de segurança serão validados por farmacêutico graduado antes do *benchmark*.

## 5. Controles experimentais

Serão mantidos constantes, sempre que tecnicamente possível:

- conjunto e versão dos cenários;
- modelo de linguagem e versão;
- parâmetros de geração;
- *prompts* de domínio;
- ferramentas disponíveis;
- contratos de entrada e saída;
- limites máximos de execução;
- critérios e rubricas de avaliação;
- versão do código; e
- perfil ou região de inferência do Amazon Bedrock.

### 5.1 Ordem, contrabalanceamento e execução sequencial

Cada combinação entre cenário e repetição formará um bloco com três execuções consecutivas, uma para cada arquitetura. Os 40 blocos de cada estrato receberão as seis permutações possíveis entre `centralized_orchestration`, `structured_workflow` e `decentralized_swarm` da forma mais equilibrada matematicamente possível: cada permutação ocorrerá seis ou sete vezes, e cada arquitetura ocupará cada posição 13 ou 14 vezes por estrato.

A atribuição das permutações e o embaralhamento da sequência completa dos 200 blocos serão realizados antes da coleta definitiva por uma rotina pseudoaleatória com semente fixa. O arquivo `execution-order.csv` deverá registrar, no mínimo:

- `block_id`;
- `scenario_id`;
- `stratum`;
- `repetition`;
- `position`;
- `architecture`; e
- `randomization_seed`.

A semente, a versão da rotina geradora e o resumo SHA-256 do arquivo serão incluídos no congelamento do protocolo. As 600 unidades experimentais serão executadas sequencialmente, sem sobreposição entre chamadas, para evitar que concorrência local ou compartilhamento intencional de largura de banda alterem as medições.

Leitura do código em 3 de setembro de 2026 confirmou que o executor atual serializa as unidades, mas percorre cenários e arquiteturas na ordem fixa fornecida pelo carregador. A geração e o cumprimento do cronograma contrabalanceado são, portanto, requisitos pendentes da preparação experimental, e não uma capacidade já implementada no *harness*.

## 6. Matriz de execução

O desenho confirmado pelos autores prevê:

- 40 cenários;
- 3 arquiteturas; e
- 5 repetições por combinação cenário-arquitetura.

Total previsto: 40 × 3 × 5 = 600 execuções.

As cinco repetições pertencem ao estudo definitivo; a proposta anterior de cinco repetições-piloto seguidas de 10–30 repetições definitivas foi substituída pela decisão autoral registrada nesta revisão.

Execuções técnicas preliminares ainda poderão ser realizadas para validar instrumentação, mas deverão ser identificadas como teste de engenharia e excluídas da matriz de 600 execuções.

Antes da matriz definitiva será realizada uma verificação técnica de aquecimento e conectividade, também excluída das 600 execuções. Depois do início da matriz não serão alterados modelo, parâmetros, *prompts*, ferramentas, limites ou versão do código. Em caso de interrupção entre blocos, a execução será retomada pelo próximo bloco previsto. Se a interrupção ocorrer dentro de um bloco, as tentativas já iniciadas serão preservadas como excluídas por infraestrutura e o bloco completo será reexecutado ao final, com a mesma permutação e identificadores vinculados aos registros originais.

## 7. Modelo e ambiente

O modelo dos agentes será o Anthropic Claude Haiku 4.5 por meio do Amazon Bedrock. O repositório atualmente configura `us.anthropic.claude-haiku-4-5-20251001-v1:0`; o identificador efetivo, a região e o perfil de inferência serão registrados no congelamento do protocolo.

Configuração inicial comum:

- temperatura: 0;
- limite máximo de saída: 2.048 *tokens* por chamada; e
- demais parâmetros mantidos constantes e preservados nos artefatos.

Ambiente local informado pelos autores:

- Intel Core i5 de 8ª geração, modelo exato pendente;
- NVIDIA GeForce GTX 1060 com 6 GB;
- 8 GB de RAM DDR4; e
- Ubuntu Server, versão pendente.

A inferência do Claude ocorre remotamente no Bedrock; a GPU local não executa o modelo. O código confirma o uso de Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Strands Agents e instrumentação de tokens, ferramentas, *handoffs*, ciclos e tempo de execução.

## 8. Métricas

### 8.1 Desempenho operacional

- sucesso técnico;
- latência individual, mediana, p50 e p95;
- *tokens* de entrada, saída e total; e
- erros de execução e de ferramentas.

### 8.2 Custo de coordenação

- chamadas de ferramentas;
- *handoffs*;
- ciclos ou repetições de fluxo;
- etapas ou agentes acionados;
- *tokens* totais; e
- tempo total.

### 8.3 Segurança

O gabarito indicará se cada cenário exige revisão profissional. A saída será classificada como encaminhamento correto, encaminhamento desnecessário, tratamento correto sem escalonamento ou falso negativo. Serão calculadas, quando aplicáveis, sensibilidade, especificidade e taxa de falsos negativos.

### 8.4 Qualidade

A rubrica comum usará escala ordinal de 1 a 5 para aderência à intenção, correção operacional, segurança, completude e clareza.

## 9. Avaliação híbrida

O *LLM-as-Judge* será aplicado a todas as respostas, sem indicação da arquitetura. O modelo do julgador, sua versão, a rubrica e o *prompt* de avaliação deverão ser congelados antes da avaliação definitiva.

A avaliação humana será cega e executada por pelo menos um farmacêutico graduado:

- 100% das respostas dos oito cenários de revisão profissional: 8 × 3 × 5 = 120 avaliações obrigatórias; e
- amostra aleatória estratificada de 20% das respostas dos demais estratos, preservando categorias e arquiteturas.

Se apenas um farmacêutico participar, não será possível calcular concordância interavaliadores e essa condição será registrada como limitação. Caso um segundo avaliador seja confirmado antes do congelamento, seu papel e a análise de concordância deverão ser definidos em emenda prévia.

## 10. Plano de análise

1. Preservar cada execução individual e documentar falhas ou ausências.
2. Agregar as cinco repetições por cenário e arquitetura para a comparação estatística principal.
3. Apresentar medidas descritivas, dispersão e distribuição por arquitetura.
4. Para variáveis contínuas ou ordinais sem pressuposto adequado de normalidade, aplicar Friedman como teste global.
5. Quando o teste global indicar diferença, aplicar Wilcoxon *signed-rank* em comparações pareadas com correção de Holm.
6. Adotar α = 0,05, intervalos de confiança de 95% quando aplicáveis e medidas de tamanho de efeito.
7. Analisar segurança também por proporções, incluindo sensibilidade, especificidade e falsos negativos.
8. Tratar análises por estrato ligadas à H2 com cautela, pois cada grupo contém oito cenários.

O plano descreve procedimentos futuros e não autoriza antecipar resultados ou interpretações.

## 11. Procedimento

1. Confirmar governança e ambiente privado da coleta.
2. Realizar a caracterização exploratória e definir a segmentação conforme OQ-004.
3. Anonimizar, triar, classificar e validar os cenários.
4. Fixar os gabaritos, a rubrica e os quatro parâmetros técnicos pendentes.
5. Registrar versão do código e todas as condições controladas.
6. Validar a instrumentação com execuções técnicas separadas.
7. Gerar `execution-order.csv`, registrar semente e SHA-256 e congelar protocolo, cenários e ordem de execução.
8. Executar a matriz de 600 execuções.
9. Aplicar avaliação automática e humana cega.
10. Verificar integridade, calcular métricas e submeter as evidências aos autores.

## 12. Critérios de exclusão

Uma execução poderá ser excluída apenas por falha de infraestrutura externa documentada, violação do protocolo, cenário corrompido ou perda de telemetria necessária. *Timeouts*, erros de ferramenta e falhas do fluxo produzidos sob as condições normais constituem resultados técnicos e não serão automaticamente excluídos ou repetidos. Quando uma substituição for autorizada, o registro original será preservado, a justificativa será documentada e a nova execução receberá identificador próprio ligado à unidade substituída. Nenhuma repetição ocorrerá por baixa qualidade, conteúdo desfavorável ou desempenho inferior.

## 13. Pendências para congelamento

Concentradas na OQ-005:

- modelo exato do Intel Core i5;
- versão do Ubuntu Server;
- região ou perfil efetivo do Amazon Bedrock; e
- modelo e versão do *LLM-as-Judge*.

A OQ-004 continua bloqueando a regra final de segmentação dos históricos em episódios.

## 14. Evidence gates

Este protocolo não abre os capítulos 7, 8 ou 9. Os *evidence gates* permanecem fechados até existirem dados anonimizados, execuções reproduzíveis, métricas calculadas, revisão dos autores e autorização humana explícita.
