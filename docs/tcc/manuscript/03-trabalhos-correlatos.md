# 3 TRABALHOS CORRELATOS

Este capítulo analisa trabalhos que se aproximam do problema investigado sob dois eixos complementares: a automação de serviços farmacêuticos e de saúde com modelos de linguagem; e o emprego de sistemas multiagentes em tarefas que exigem especialização, coordenação e controle. A seleção prioriza estudos revisados por pares, publicados em fontes primárias e com descrição suficiente da arquitetura ou do método de avaliação. Revisões amplas permanecem na fundamentação teórica, enquanto esta seção concentra soluções comparáveis ao objeto da pesquisa.

A comparação considera quatro aspectos: domínio e tarefa; forma de decomposição ou coordenação; estratégia de avaliação; e distância em relação ao MAB. Esse recorte evita equiparar sistemas apenas porque utilizam LLMs ou múltiplos componentes. Um sistema pode ser relevante por operar no domínio farmacêutico, mas não comparar arquiteturas; outro pode estudar coordenação de agentes de forma rigorosa, porém fora do contexto de farmácias. A contribuição de cada trabalho é analisada dentro desses limites.

## 3.1 SISTEMAS DE ATENDIMENTO AUTOMATIZADO

Pais et al. (2024) desenvolveram o MEDIC para identificar e corrigir instruções de uso de medicamentos potencialmente incorretas em farmácias on-line. A solução combina um modelo ajustado com lógica farmacêutica explícita, salvaguardas e ciclos de revisão por farmacêuticos. O estudo é especialmente relevante por tratar uma aplicação real de alto risco e por não reduzir a qualidade à fluência da resposta: conhecimento do domínio, regras de segurança e validação profissional integram o desenho do sistema. Entretanto, o MEDIC é uma solução especializada para instruções de medicamentos e não compara formas de coordenação entre agentes.

Jagatap, Merugu e Comar (2025) apresentam o RxLens, sistema implantado para converter prescrições em carrinhos de compra em farmácias digitais. O fluxo encadeia supressão de informações pessoais, reconhecimento óptico de caracteres, extração de medicamentos, recuperação em catálogo e rastreabilidade por caixas delimitadoras. O trabalho demonstra que tarefas farmacêuticas podem ser decompostas em etapas verificáveis e que a avaliação automática deve ser confrontada com julgamentos humanos. Apesar do título empregar o termo multiagente, a contribuição central é um pipeline especializado; não há comparação controlada entre orquestração, workflow e coordenação descentralizada.

Dou et al. (2025) propõem o ShennongMGS, sistema de orientação sobre medicamentos em língua chinesa que integra informações heterogêneas em um grafo de conhecimento e utiliza um LLM especializado para orientação medicamentosa e previsão de reações adversas. A avaliação envolve profissionais de saúde e especialistas em IA, o que reforça a necessidade de conhecimento estruturado e supervisão especializada em aplicações sensíveis. Sua proximidade com o tema está no atendimento sobre medicamentos; sua limitação para esta pesquisa é concentrar-se na especialização do modelo e da base de conhecimento, e não na arquitetura de coordenação.

Em conjunto, esses estudos mostram que a automação farmacêutica exige decomposição de tarefas, evidência rastreável, mecanismos de segurança e participação profissional. Eles sustentam o domínio e os critérios de qualidade do MAB, mas não respondem à pergunta arquitetural desta pesquisa: como diferentes estratégias de coordenação se comportam quando submetidas aos mesmos cenários de atendimento.

## 3.2 SISTEMAS MULTIAGENTES APLICADOS

Pandey, Amod e Kumar (2024) investigam um sistema multiagente para automatizar a justificativa de necessidade médica em processos de autorização prévia. Agentes especializados dividem a comparação entre prontuários e diretrizes clínicas em subtarefas, produzindo julgamentos acompanhados de evidências. O estudo aproxima sistemas multiagentes de um fluxo real de saúde e evidencia o valor da especialização e da explicabilidade. Contudo, avalia estratégias de prompting e modelos, não arquiteturas alternativas de coordenação sob o mesmo protocolo.

Lu et al. (2024) apresentam o TriageAgent, estrutura heterogênea para triagem clínica. Os agentes assumem papéis distintos, participam de discussões em múltiplas rodadas e utilizam autoconfiança, encerramento antecipado e recuperação de conhecimento a partir do Emergency Severity Index. O trabalho é relevante porque torna explícitos mecanismos de colaboração e parada em um domínio sensível. Ainda assim, avalia uma arquitetura proposta contra métodos de referência, em vez de isolar o efeito de diferentes topologias de coordenação.

Wang et al. (2025) deslocam a análise do nome dos frameworks para os mecanismos concretos de colaboração. Os autores organizam as estratégias em governança, controle de participação, dinâmica de interação e gestão do histórico, relacionando essas dimensões à qualidade da tarefa e à eficiência computacional. Essa operacionalização é diretamente útil ao MAB, pois permite descrever orquestração, workflow e swarm por características observáveis. O estudo, porém, utiliza tarefas gerais dependentes de contexto e não incorpora requisitos farmacêuticos de segurança ou encaminhamento profissional.

Kim et al. (2026) realizam uma comparação controlada de arquiteturas de agentes baseados em modelos de linguagem, abrangendo configurações de agente único, independentes, centralizadas, descentralizadas e híbridas. O estudo mostra que o efeito da colaboração depende da decomponibilidade da tarefa, da capacidade do modelo e do custo de coordenação. Entre os trabalhos selecionados, é o mais próximo do desenho comparativo do MAB. A diferença fundamental está no domínio: seus benchmarks não representam atendimentos farmacêuticos nem as restrições operacionais e de segurança desse contexto.

Esses trabalhos confirmam que especialização, governança, circulação de contexto e mecanismos de parada são variáveis arquiteturais relevantes. Ao mesmo tempo, nenhum deles combina uma comparação controlada de orquestração centralizada, workflow estruturado e swarm com cenários equivalentes de atendimento em farmácias e avaliação híbrida orientada à segurança.

## 3.3 ANÁLISE DOS TRABALHOS CORRELATOS

O Quadro 1 sintetiza a relação entre os trabalhos selecionados e esta pesquisa. A comparação não pretende ordenar soluções de domínios distintos, mas explicitar quais dimensões cada estudo cobre e quais permanecem fora de seu escopo.

| Trabalho | Domínio e tarefa | Arquitetura ou método | Relação com o MAB |
| --- | --- | --- | --- |
| Pais et al. (2024) | Farmácia on-line; prevenção de erros em instruções | LLM especializado, lógica farmacêutica, salvaguardas e revisão profissional | Forte aderência ao domínio e à segurança; não compara coordenação multiagente |
| Jagatap, Merugu e Comar (2025) | Farmácia digital; processamento de prescrições | Pipeline com supressão de dados pessoais, OCR, extração, recuperação e rastreabilidade | Demonstra decomposição operacional; não isola o efeito da arquitetura |
| Dou et al. (2025) | Orientação sobre medicamentos | Grafo de conhecimento e LLM especializado | Aproxima atendimento medicamentoso e avaliação especializada; não é estudo de coordenação |
| Pandey, Amod e Kumar (2024) | Saúde; autorização prévia | Agentes especializados com julgamentos baseados em evidências | Demonstra decomposição multiagente em saúde; não compara topologias |
| Lu et al. (2024) | Saúde; triagem clínica | Agentes heterogêneos, discussão, autoconfiança, RAG e parada antecipada | Explicita colaboração e controle; avalia uma arquitetura específica |
| Wang et al. (2025) | Tarefas gerais dependentes de contexto | Dimensões de governança, participação, interação e histórico | Oferece critérios para caracterizar coordenação; não cobre o domínio farmacêutico |
| Kim et al. (2026) | Benchmarks gerais de raciocínio e colaboração | Comparação de arquiteturas centralizadas, descentralizadas e híbridas | Correlato metodológico mais próximo; não inclui atendimento farmacêutico |

Fonte: elaboração própria.

A análise evidencia duas aproximações parciais. Os estudos farmacêuticos possuem alta aderência ao domínio, mas tratam sistemas especializados ou pipelines únicos. Os estudos multiagentes tornam a coordenação observável e comparável, porém avaliam tarefas clínicas, administrativas ou gerais que não reproduzem a diversidade do atendimento em farmácias. Essa separação impede transportar diretamente resultados de um grupo para o outro.

Também há diferenças de avaliação. Pais et al. (2024), Dou et al. (2025), Pandey, Amod e Kumar (2024) e Lu et al. (2024) incorporam conhecimento especializado, evidências ou participação profissional. Wang et al. (2025) e Kim et al. (2026) oferecem maior controle sobre mecanismos arquiteturais e custos de colaboração. O desenho do MAB aproxima essas duas exigências ao manter cenários e variáveis controladas entre arquiteturas e prever métricas operacionais, avaliação por LLM e revisão humana estratificada. Trata-se do protocolo proposto; nenhum resultado é antecipado neste capítulo.

## 3.4 LACUNAS E OPORTUNIDADES

A primeira lacuna é de interseção: não foi identificado, entre os trabalhos selecionados, um estudo que compare orquestração centralizada, workflow estruturado e swarm no mesmo conjunto de atendimentos farmacêuticos. Soluções diretamente ligadas a farmácias privilegiam uma tarefa e uma arquitetura; comparações arquiteturais amplas utilizam outros domínios.

A segunda lacuna é de controle experimental. Comparar sistemas construídos para tarefas diferentes não permite atribuir variações de qualidade, custo ou latência à estratégia de coordenação. Para reduzir esse problema, o MAB propõe manter constantes cenários, ferramentas, modelo de linguagem, critérios de avaliação e número de repetições, alterando prioritariamente a forma de distribuir controle e comunicação.

A terceira lacuna envolve segurança e avaliação. Métricas operacionais são necessárias para observar tokens, latência, ferramentas e transferências, mas não bastam para julgar respostas em saúde. Os trabalhos farmacêuticos e clínicos reforçam a necessidade de salvaguardas, evidência e revisão profissional. Por isso, o protocolo do MAB prevê avaliação híbrida e encaminhamento ao farmacêutico em situações sensíveis, sem atribuir autonomia clínica ao sistema.

Assim, a oportunidade de pesquisa está em aproximar o rigor das comparações arquiteturais das exigências práticas do atendimento farmacêutico. O MAB se posiciona como um estudo comparativo dessa interseção. Sua contribuição pretendida é produzir evidências sobre os efeitos da coordenação no contexto delimitado; a confirmação de qualquer vantagem, limitação ou contribuição permanece condicionada à execução e à validação dos experimentos.
