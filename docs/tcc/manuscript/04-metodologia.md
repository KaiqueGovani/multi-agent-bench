# 4 METODOLOGIA

## 4.1 TIPO DE PESQUISA

O trabalho caracteriza-se como pesquisa aplicada, bibliográfica, tecnológica e experimental. É aplicada porque busca produzir conhecimento utilizável na construção de um sistema de atendimento; bibliográfica porque organiza conceitos e evidências publicados sobre agentes e coordenação; tecnológica porque envolve modelagem e implementação de um protótipo; e experimental porque compara arquiteturas sob condições controladas. A comparação será realizada somente após o congelamento do protocolo e a preparação do conjunto de cenários.

## 4.2 ETAPAS DO TRABALHO

A revisão bibliográfica realizada até este estágio é classificada como revisão estruturada da literatura, e não como revisão sistemática. Foram usadas expressões relacionadas a sistemas multiagentes baseados em LLMs, orquestração, workflow, swarm, agentes distribuídos, avaliação de agentes e IA aplicada a farmácias. As fontes foram localizadas em páginas de editoras, bibliotecas digitais, repositórios de preprints e documentos institucionais. A rastreabilidade é mantida no registro vivo de referências, que armazena URL, prioridade, tipo, seção-alvo e decisão editorial.

Os critérios de inclusão priorizam trabalhos que: definam ou organizem sistemas multiagentes; discutam arquiteturas de coordenação; comparem empiricamente estratégias arquiteturais; proponham métricas de avaliação; ou contextualizem o atendimento farmacêutico. São excluídos textos sem relação direta com a pergunta de pesquisa, materiais de marketing usados como única sustentação científica e referências cujo metadado primário não possa ser verificado. A revisão não reivindica exaustividade, protocolo PRISMA, dupla triagem independente ou cobertura completa de bases indexadas, pois essas etapas não foram executadas e documentadas.

O desenvolvimento tecnológico foi dividido em quatro etapas: modelagem de uma interface comum de execução; implementação das arquiteturas centralizada, workflow e swarm; instrumentação de eventos e métricas; e preparação dos cenários comparáveis. A etapa experimental utilizará a mesma entrada, conjunto de ferramentas, modelo, configuração e limites operacionais para as três arquiteturas. Ordem de execução, repetições, seed quando disponível, versão do código e parâmetros do modelo deverão ser preservados junto aos artefatos do experimento.

A origem e a transformação dos cenários derivados de conversas de WhatsApp permanecem pendentes da OQ-001. Até a decisão dos autores, nenhum dado real será copiado para o repositório e o protocolo utilizará apenas o esquema de campos e cenários sintéticos já existentes.

## 4.3 DEFINIÇÃO DO PROBLEMA E HIPÓTESES

A pergunta de pesquisa é: como a escolha entre orquestração centralizada, workflow estruturado e coordenação descentralizada por handoffs influencia a eficiência operacional, a qualidade das respostas e o custo de coordenação de um sistema de atendimento farmacêutico, quando as demais condições são mantidas constantes?

As hipóteses foram formuladas de maneira não direcional para evitar presumir uma arquitetura vencedora antes dos testes:

- H0: não existe diferença estatisticamente detectável entre as arquiteturas nas métricas primárias definidas no protocolo.
- H1: pelo menos uma arquitetura apresenta diferença estatisticamente detectável em uma ou mais métricas primárias.
- H2: o efeito da arquitetura depende do tipo de cenário, especialmente da necessidade de ferramentas, anexos, continuidade de contexto ou revisão humana.

As hipóteses permanecem com status de proposta até aprovação dos autores e congelamento do protocolo. Qualquer alteração posterior à coleta deverá ser identificada como exploratória e registrada no histórico.
