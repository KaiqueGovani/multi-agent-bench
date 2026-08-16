# 3 TRABALHOS CORRELATOS

Este capítulo apresenta os trabalhos mais relevantes para a fundamentação desta pesquisa, com foco em sistemas multiagentes e arquiteturas de coordenação aplicadas a tarefas complexas de atendimento inteligente. Como o objetivo central do trabalho é comparar diferentes formas de coordenação entre agentes, foram priorizados estudos que discutem organização do fluxo, distribuição de tarefas, centralização ou descentralização da decisão e efeitos dessas escolhas sobre desempenho, escalabilidade e controle.

Os trabalhos analisados neste capítulo tratam de temas complementares ao desenvolvimento desta pesquisa. De um lado, foram considerados estudos sobre sistemas multiagentes, arquiteturas de coordenação, workflows e abordagens descentralizadas, pois esses temas ajudam a compreender como diferentes agentes podem ser organizados para executar tarefas de forma cooperativa. De outro lado, foram considerados trabalhos relacionados ao uso de inteligência artificial em farmácias e serviços farmacêuticos, pois eles aproximam a discussão teórica do contexto prático escolhido para este projeto.

A relação entre esses dois grupos de trabalhos é importante porque o objetivo desta pesquisa não é apenas propor um sistema de atendimento automatizado, mas analisar como diferentes formas de coordenação entre agentes podem influenciar o comportamento do sistema. Assim, as referências sobre sistemas multiagentes contribuem para a fundamentação técnica da arquitetura, enquanto os trabalhos ligados ao contexto farmacêutico ajudam a justificar o domínio de aplicação e os tipos de problema que podem surgir em atendimentos reais.

A literatura recente mostra que a discussão sobre sistemas multiagentes baseados em LLMs vem se consolidando em torno de três questões principais: como estruturar os agentes, como coordená-los e em quais tipos de tarefa cada arquitetura produz melhores resultados. Trabalhos mais amplos de revisão oferecem taxonomias e desafios gerais, enquanto estudos mais específicos tratam de workflow, swarm, descentralização e aplicações em domínios particulares, como serviços farmacêuticos.

## 3.1 SISTEMAS DE ATENDIMENTO AUTOMATIZADO

Jagatap, Merugu e Comar (2025) investigam a automação do processamento de prescrições no contexto farmacêutico digital. A metodologia consiste em uma solução em etapas, ou pipeline, baseada em LLM, OCR, extração de medicamentos e correspondência com catálogo. Nesse caso, pipeline significa uma sequência organizada de etapas, em que a saída de uma etapa serve como entrada para a próxima.

Como resultado, o sistema melhora o Recall@3 em relação a métodos anteriores. O termo recall é uma métrica usada para medir a capacidade de um sistema encontrar corretamente os itens relevantes. No caso do Recall@3, verifica-se se a resposta correta aparece entre as três primeiras sugestões retornadas pelo sistema. Essa métrica é relevante no contexto farmacêutico porque, ao buscar medicamentos ou informações em um catálogo, não basta o sistema responder rápido; ele precisa recuperar corretamente as opções mais adequadas. Portanto, a menção ao recall ajuda a mostrar que aplicações de IA em farmácias também precisam ser avaliadas por métricas objetivas de qualidade, e não apenas por funcionamento geral.

Esse trabalho contribui para a presente pesquisa por demonstrar que o domínio farmacêutico possui tarefas que podem ser divididas em etapas e apoiadas por agentes ou componentes especializados. Entretanto, seu foco está na automação de uma tarefa específica, e não na comparação entre diferentes arquiteturas de coordenação. Essa diferença reforça a lacuna explorada pelo presente trabalho.

Hatzimanolis et al. (2025) tratam do uso atual de IA na prática farmacêutica. A metodologia é uma scoping review, ou revisão de escopo, voltada a mapear como a IA vem sendo aplicada na área. Os resultados indicam que muitas aplicações ainda estão ligadas à gestão de fluxo, produtividade, triagem e apoio operacional, mais do que à melhoria direta de desfechos clínicos.

Esse estudo é relevante porque ajuda a justificar a farmácia como cenário de aplicação. O atendimento farmacêutico envolve solicitações variadas, organização de informações, encaminhamento de demandas e necessidade de respostas consistentes. Essas características tornam o ambiente adequado para testar arquiteturas multiagentes voltadas ao atendimento inteligente.

## 3.2 SISTEMAS MULTIAGENTES APLICADOS

Li et al. (2024) tratam como problema central a ausência de uma síntese sistemática sobre a construção de sistemas multiagentes baseados em LLMs. A metodologia do estudo é uma revisão organizada em torno de componentes como perfil dos agentes, percepção, ação individual, interação e evolução. Como resultado, os autores propõem uma estrutura de análise para compreender como agentes são organizados e como interagem entre si.

Esse trabalho é relevante porque mostra que um sistema multiagente não depende apenas da capacidade individual de cada agente, mas também da forma como eles são coordenados. Para esta pesquisa, essa discussão serve como base para analisar por que diferentes arquiteturas podem gerar resultados distintos em um mesmo cenário de atendimento.

Piccialli et al. (2025) abordam agentes autônomos em ambientes de inteligência artificial distribuída. O problema tratado pelos autores está na fragmentação da literatura sobre agentes colaborativos e autônomos. A metodologia consiste em uma revisão ampla, organizada em forma de taxonomia, e o resultado principal é a consolidação de uma visão sobre como agentes podem colaborar para ampliar flexibilidade, robustez e escalabilidade.

A contribuição desse estudo para o presente trabalho está na relação entre colaboração e desempenho. Em um atendimento farmacêutico automatizado, diferentes agentes podem assumir funções distintas, como interpretar a solicitação, consultar informações, validar respostas e encaminhar demandas. Por isso, compreender como agentes colaboram ajuda a justificar a proposta de comparar arquiteturas de coordenação.

Balaprakash et al. (2025) tratam das limitações de modelos tradicionais de workflow em ambientes distribuídos. O trabalho propõe uma estrutura descentralizada baseada em swarm intelligence, ou inteligência de enxame. Esse conceito se refere a sistemas nos quais múltiplos agentes simples interagem entre si e produzem um comportamento coletivo, sem depender totalmente de um controlador central.

Esse estudo é relevante porque aproxima a discussão da arquitetura swarm, uma das abordagens consideradas neste projeto. A lógica descentralizada pode oferecer maior flexibilidade, mas também pode trazer desafios de controle, rastreabilidade e consistência. Essa tensão é importante para a comparação proposta neste trabalho.

Kim et al. (2025; 2026) abordam diretamente um problema próximo ao desta monografia: como a arquitetura de coordenação afeta o desempenho de sistemas de agentes. A metodologia é experimental e compara diferentes arquiteturas, como agente único, arquitetura centralizada, descentralizada e híbrida, em múltiplos benchmarks. Nesse contexto, benchmark significa um conjunto de testes padronizados usado para comparar o desempenho de diferentes soluções. Os autores também utilizam o termo baseline, que representa um resultado de referência usado como ponto de comparação.

Os resultados mostram que não existe uma arquitetura universalmente melhor. Sistemas multiagentes podem superar o baseline em tarefas que podem ser divididas entre agentes, mas também podem apresentar desempenho inferior quando a tarefa exige uma sequência rígida de passos ou quando a coordenação entre agentes é inadequada. Essa conclusão é central para esta pesquisa, pois reforça a necessidade de comparar, no mesmo contexto farmacêutico, arquiteturas como orquestração, workflow e swarm.

## 3.3 COMPARAÇÃO COM SOLUÇÕES EXISTENTES

> O quadro comparativo permanece no DOCX e deverá ganhar versão tabular versionável.

## 3.4 LACUNAS IDENTIFICADAS

Os trabalhos analisados mostram que a literatura já apresenta avanços importantes em sistemas multiagentes, arquiteturas de coordenação e aplicações de IA no setor farmacêutico. No entanto, esses temas aparecem, em grande parte, de forma separada. Os estudos sobre sistemas multiagentes explicam como agentes podem ser estruturados e coordenados, enquanto os trabalhos sobre farmácia mostram aplicações práticas de IA nesse domínio.

A lacuna identificada está justamente na comparação entre diferentes arquiteturas de coordenação dentro de um mesmo contexto farmacêutico. Em outras palavras, ainda há espaço para investigar como modelos como orquestração centralizada, workflow estruturado e swarm se comportam quando aplicados ao mesmo tipo de atendimento. Essa comparação é importante porque a escolha da arquitetura pode influenciar tempo de resposta, distribuição de tarefas, qualidade das respostas, necessidade de intervenção humana e controle do processo.

O quadro 1 mostra que os estudos mais próximos do núcleo do MAB são os que tratam explicitamente de estrutura, coordenação e descentralização. Já os trabalhos em farmácia ajudam mais a justificar o cenário de aplicação do que a responder diretamente ao problema arquitetural. Em outras palavras, a literatura já mostra que farmácia é um contexto válido para automação e IA, mas ainda oferece pouco suporte comparativo sobre qual modelo de coordenação entre agentes é o mais adequado para esse tipo de serviço.

Com base nos trabalhos selecionados, observa-se uma lacuna clara: há revisões e taxonomias importantes sobre sistemas multiagentes, há propostas de coordenação descentralizada e há aplicações em farmácia, mas são menos frequentes os estudos que colocam, lado a lado, arquiteturas diferentes sob um mesmo contexto experimental para avaliar seus efeitos de forma comparável. É exatamente nesse ponto que esta pesquisa se posiciona.

As referências escolhidas foram mantidas porque sustentam, cada uma, uma parte essencial do problema: Li et al. e Piccialli et al. organizam o campo dos sistemas multiagentes; Balaprakash et al. e Kim et al. aproximam a discussão da comparação arquitetural entre centralização, workflow e descentralização; Jagatap et al. e Hatzimanolis et al. justificam a escolha da farmácia como estudo de caso operacional. Assim, o capítulo preserva o foco central nas arquiteturas de agentes, enquanto o domínio farmacêutico permanece como contexto aplicado. Tudo o que diz respeito à arquitetura proposta, ao fluxo de desenvolvimento, à implementação do protótipo e aos experimentos comparativos será detalhado no capítulo de metodologia.
