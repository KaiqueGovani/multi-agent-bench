# 2 FUNDAMENTAÇÃO TEÓRICA

## 2.1 INTELIGÊNCIA ARTIFICIAL NO ATENDIMENTO

### 2.1.1 Conceitos de inteligência artificial

A inteligência artificial compreende métodos computacionais capazes de executar tarefas que exigem percepção, inferência, aprendizagem, planejamento ou produção de linguagem. No escopo deste trabalho, o interesse não está em reproduzir toda a amplitude do campo, mas em compreender sistemas que recebem uma solicitação em linguagem natural, selecionam ações, consultam fontes externas e produzem uma resposta. Essa delimitação diferencia o protótipo de um chatbot baseado apenas em respostas pré-programadas: o comportamento depende do contexto, das ferramentas disponíveis e da estratégia de coordenação definida para os agentes.

### 2.1.2 IA aplicada ao atendimento ao cliente

Em operações de atendimento, a IA pode apoiar classificação de intenção, recuperação de informações, encaminhamento de demandas, composição de respostas e identificação de casos que exigem intervenção humana. A utilidade prática, entretanto, não deve ser avaliada somente pela fluência do texto. Um sistema de atendimento também precisa responder dentro de limites de tempo, acionar a ferramenta correta, preservar o contexto da conversa e encaminhar situações sensíveis. Por isso, o presente trabalho combina medidas de eficiência operacional com critérios de qualidade e segurança.

### 2.1.3 Uso de IA em saúde e farmácias

O uso de IA em saúde exige cautela adicional porque uma resposta inadequada pode afetar decisões individuais. O protótipo desenvolvido não realiza diagnóstico nem prescrição e não deve fornecer dosagens específicas. Seu domínio é o atendimento operacional de farmácia, incluindo perguntas frequentes, consulta de disponibilidade de produtos, processamento inicial de anexos e direcionamento para revisão profissional quando necessário. Essa fronteira funcional é coerente com a ampliação do papel das farmácias comunitárias, que passaram a oferecer serviços para além da dispensação de medicamentos, mantendo o farmacêutico como profissional responsável por orientações clínicas e uso seguro de medicamentos (WHO EUROPE, 2024).

## 2.2 LARGE LANGUAGE MODELS E AGENTES INTELIGENTES

### 2.2.1 Conceito de LLM

Large Language Models (LLMs) são modelos treinados em grandes coleções de texto para estimar e gerar sequências linguísticas. Quando empregados isoladamente, podem interpretar instruções e produzir respostas, mas não garantem, por si só, acesso a dados atualizados, execução de ações ou observância de regras de negócio. Essas capacidades adicionais dependem da arquitetura que envolve o modelo.

### 2.2.2 Uso de LLM em agentes

Um agente baseado em LLM associa o modelo a um objetivo, um conjunto de instruções, estado de execução e mecanismos de ação. O agente pode selecionar ferramentas, interpretar seus retornos e decidir como prosseguir. Li et al. (2024) organizam sistemas desse tipo em componentes como perfil, percepção, ação individual, interação e evolução. Essa visão é útil para separar a capacidade linguística do modelo das responsabilidades arquiteturais necessárias para operar um sistema completo.

### 2.2.3 Ferramentas e integração

Ferramentas conectam o agente a funções determinísticas ou serviços externos. No MAB, elas representam operações como consulta de perguntas frequentes, busca de estoque e análise inicial de anexos. A ferramenta devolve evidência estruturada; o agente decide quando acioná-la e como incorporar seu retorno. Essa separação melhora a observabilidade, pois chamadas, erros, tempo de execução e transições entre agentes podem ser registrados independentemente do texto final.

## 2.3 SISTEMAS MULTIAGENTES

### 2.3.1 Definição e características

Um sistema multiagente é composto por múltiplas unidades capazes de perceber informações, tomar decisões e atuar de maneira coordenada. Em sistemas baseados em LLMs, os agentes podem ser diferenciados por instruções, funções e ferramentas. A especialização permite decompor uma solicitação em responsabilidades menores, mas introduz custos de comunicação, sincronização e controle. Assim, adicionar agentes não implica automaticamente melhorar o desempenho.

### 2.3.2 Arquitetura de sistemas multiagentes

A arquitetura define quais agentes existem, quem inicia a execução, como o estado é compartilhado e quem produz a resposta final. Revisões recentes destacam que sistemas multiagentes podem variar quanto à autonomia, topologia de comunicação, distribuição das decisões e mecanismos de supervisão (LI et al., 2024; PICCIALLI et al., 2025). Essas escolhas influenciam rastreabilidade, robustez e custo computacional, além de determinar quais eventos podem ser observados durante um atendimento.

### 2.3.3 Comunicação e coordenação entre agentes

A comunicação pode ocorrer por mensagens diretas, estado compartilhado, handoffs ou por um controlador que intermedeia as decisões. Ela é necessária para distribuir subtarefas, mas também pode propagar erros ou ampliar divergências. Hammond et al. (2025) organizam riscos multiagentes em categorias que incluem descoordenação, conflito e cooperação indesejada. Embora o MAB opere com agentes que compartilham um objetivo, o risco de descoordenação permanece relevante quando uma rota incorreta, uma evidência insuficiente ou uma transferência excessiva altera o atendimento.

## 2.4 ARQUITETURAS DE COORDENAÇÃO

### 2.4.1 Orquestração centralizada

Na orquestração centralizada, um supervisor concentra as decisões de classificação, seleção de ferramentas ou agentes e composição da resposta. A principal vantagem é a existência de um ponto claro de controle, que simplifica a aplicação de políticas e a reconstrução do fluxo. Como contrapartida, o supervisor pode se tornar gargalo e ponto único de falha. No MAB, a arquitetura centralizada utiliza um agente supervisor que escolhe entre ferramentas de FAQ, estoque e anexos e produz a resposta final.

### 2.4.2 Workflow estruturado

O workflow organiza a execução em etapas previamente definidas. No protótipo, o fluxo inclui classificação, coleta de evidência, análise multimodal quando aplicável, revisão e síntese. Cada etapa possui responsabilidade explícita e ordem estável. A previsibilidade facilita testes e auditoria, mas reduz a flexibilidade para alterar o caminho durante a execução. A revisão de Yu et al. (2025) mostra que workflows de agentes combinam planejamento, execução e controle em estruturas que variam de sequências fixas a fluxos adaptativos.

### 2.4.3 Sistemas descentralizados (swarm)

Em uma organização descentralizada, os agentes podem transferir a tarefa diretamente entre pares. O MAB implementa essa estratégia por meio de handoffs: um coordenador inicia a cadeia, especialistas podem delegar a outros especialistas e um sintetizador produz a resposta final. O mecanismo aumenta a autonomia local, porém exige limites de handoff e telemetria para evitar ciclos, custo excessivo ou perda de contexto.

### 2.4.4 Comparação entre arquiteturas

A adequação de uma arquitetura depende da tarefa, da capacidade do modelo e do custo de coordenação. Kim et al. (2026) compararam arquiteturas de agente único, independentes, centralizadas, descentralizadas e híbridas em diferentes benchmarks e observaram que o benefício da colaboração não cresce de forma uniforme. Essa evidência reforça a escolha metodológica deste trabalho: comparar as três arquiteturas sob os mesmos cenários, ferramentas, modelo e condições de execução, em vez de assumir antecipadamente que uma delas é superior.

## 2.5 ATENDIMENTO EM FARMÁCIAS

### 2.5.1 Estrutura do atendimento farmacêutico

O atendimento em farmácias reúne demandas administrativas, comerciais e de orientação em saúde. Perguntas sobre horário, entrega e disponibilidade podem ser tratadas por rotinas operacionais; solicitações clínicas ou ambíguas devem ser encaminhadas ao farmacêutico. Essa diversidade permite testar roteamento, uso de ferramentas, manutenção de contexto e revisão humana sem atribuir ao sistema uma autonomia clínica que ele não possui.

### 2.5.2 Desafios operacionais

Entre os desafios do domínio estão volume variável de solicitações, linguagem informal, anexos, continuidade entre mensagens e necessidade de distinguir dúvidas operacionais de situações sensíveis. A qualidade do sistema depende tanto da resposta final quanto da capacidade de reconhecer quando não deve responder autonomamente.

### 2.5.3 Oportunidades de automação

A automação é mais apropriada em tarefas repetitivas, verificáveis e de baixo risco, como localização de informação institucional ou consulta a dados estruturados. O valor do sistema multiagente está em organizar essas funções e preservar uma rota de supervisão. O objetivo experimental, portanto, é medir como a estratégia de coordenação altera eficiência, observabilidade e qualidade operacional, sem avaliar aconselhamento clínico ou substituir profissionais.
