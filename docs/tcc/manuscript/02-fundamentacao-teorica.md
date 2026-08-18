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

A comparação entre arquiteturas de coordenação não pode ser reduzida à quantidade de agentes empregados. Duas soluções com o mesmo número de agentes podem distribuir autoridade, estado e comunicação de maneiras distintas. Para analisá-las, é necessário observar pelo menos quatro dimensões: onde as decisões são concentradas; como o caminho de execução é definido; de que forma o contexto circula entre os agentes; e quais mecanismos permitem reconstruir ou interromper o fluxo. As taxonomias de Li et al. (2024) e Piccialli et al. (2025) mostram que interação, autonomia e organização são componentes próprios da arquitetura, e não apenas características do modelo de linguagem utilizado.

Na orquestração centralizada, a autoridade de roteamento permanece em um supervisor. Esse componente recebe a solicitação, seleciona especialistas ou ferramentas e pode consolidar a resposta. A concentração favorece a aplicação uniforme de políticas e oferece um ponto explícito para registrar decisões. Em contrapartida, a execução fica condicionada à capacidade do supervisor de interpretar corretamente cada etapa. Um erro de classificação pode direcionar todo o fluxo para uma rota inadequada, enquanto o acúmulo de decisões em um único componente pode ampliar latência e dependência operacional. Assim, centralização significa maior controle global, mas também maior concentração de responsabilidade.

No workflow estruturado, parte do controle deixa de estar exclusivamente em um agente e passa a ser representada pela própria sequência de etapas. O fluxo pode definir antecipadamente operações de classificação, obtenção de evidências, revisão e síntese, incluindo condições para desvio ou encerramento. Yu et al. (2025) descrevem workflows de agentes como combinações de planejamento, execução e controle que podem variar entre sequências fixas e estruturas adaptativas. A explicitação das transições favorece repetibilidade e auditoria, pois torna possível identificar em qual etapa ocorreu uma falha. Entretanto, um caminho rígido pode executar operações desnecessárias ou responder de forma limitada a solicitações que não se ajustem às rotas previstas.

Em sistemas descentralizados, a decisão de continuidade pode ser transferida entre os próprios agentes. Em vez de consultar um supervisor a cada passo, um especialista avalia o contexto recebido e realiza um handoff quando identifica outra competência necessária. Balaprakash et al. (2025) apresentam o SWARM como uma proposta de distribuição das funções tradicionalmente centralizadas de gestão de workflows, motivada por problemas de resiliência e escalabilidade. Essa autonomia local pode reduzir a dependência de um único controlador, mas exige regras para preservar contexto, limitar transferências e impedir ciclos. Também pode aumentar a comunicação e a repetição de trabalho quando mais de um agente interpreta a mesma solicitação.

Esses benefícios e custos dependem do tipo de tarefa e da capacidade dos modelos envolvidos. Kim et al. (2026) compararam configurações de agente único, independentes, centralizadas, descentralizadas e híbridas em diferentes benchmarks. Os autores observaram que os ganhos da colaboração não são uniformes: tarefas decomponíveis podem se beneficiar da divisão de trabalho, enquanto tarefas que dependem de uma sequência rígida ou de coordenação intensa podem sofrer com o custo adicional de comunicação. O estudo também indica que modelos mais capazes podem reduzir a vantagem relativa da colaboração, pois parte do trabalho distribuído pode ser resolvida por um único agente sem os mesmos custos de coordenação.

Portanto, não existe fundamento para declarar previamente uma arquitetura como superior em qualquer contexto. Uma comparação controlada precisa manter constantes os elementos que não constituem o objeto do estudo, como cenários, ferramentas disponíveis, modelo de linguagem e critérios de avaliação. Em seguida, deve observar consequências mensuráveis da coordenação, como rota percorrida, quantidade de handoffs, chamadas de ferramentas, consumo de tokens, latência, ocorrência de erros e qualidade da resposta. Essa relação entre desenho arquitetural e eventos observáveis sustenta a comparação proposta pelo MAB, sem antecipar resultados: orquestração, workflow e swarm representam formas distintas de distribuir controle, e sua adequação ao atendimento farmacêutico deve ser determinada pelas evidências do experimento.

## 2.5 ATENDIMENTO EM FARMÁCIAS

### 2.5.1 Estrutura do atendimento farmacêutico

O atendimento em farmácias reúne demandas administrativas, comerciais e de orientação em saúde. Perguntas sobre horário, entrega e disponibilidade podem ser tratadas por rotinas operacionais; solicitações clínicas ou ambíguas devem ser encaminhadas ao farmacêutico. Essa diversidade permite testar roteamento, uso de ferramentas, manutenção de contexto e revisão humana sem atribuir ao sistema uma autonomia clínica que ele não possui.

### 2.5.2 Desafios operacionais

Entre os desafios do domínio estão volume variável de solicitações, linguagem informal, anexos, continuidade entre mensagens e necessidade de distinguir dúvidas operacionais de situações sensíveis. A qualidade do sistema depende tanto da resposta final quanto da capacidade de reconhecer quando não deve responder autonomamente.

### 2.5.3 Oportunidades de automação

A automação é mais apropriada em tarefas repetitivas, verificáveis e de baixo risco, como localização de informação institucional ou consulta a dados estruturados. O valor do sistema multiagente está em organizar essas funções e preservar uma rota de supervisão. O objetivo experimental, portanto, é medir como a estratégia de coordenação altera eficiência, observabilidade e qualidade operacional, sem avaliar aconselhamento clínico ou substituir profissionais.
