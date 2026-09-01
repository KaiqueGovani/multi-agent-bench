# 2 FUNDAMENTAÇÃO TEÓRICA

## 2.1 ATENDIMENTO EM FARMÁCIAS

### 2.1.1 Estrutura do atendimento farmacêutico

O atendimento em farmácias reúne demandas administrativas, comerciais e de orientação em saúde. Perguntas sobre horário, entrega e disponibilidade podem ser tratadas por rotinas operacionais; solicitações clínicas ou ambíguas devem ser encaminhadas ao farmacêutico. Essa diversidade permite testar roteamento, uso de ferramentas, manutenção de contexto e revisão humana sem atribuir ao sistema uma autonomia clínica que ele não possui.

### 2.1.2 Desafios operacionais

Entre os desafios do domínio estão volume variável de solicitações, linguagem informal, anexos, continuidade entre mensagens e necessidade de distinguir dúvidas operacionais de situações sensíveis. A qualidade do sistema depende tanto da resposta final quanto da capacidade de reconhecer quando não deve responder autonomamente.

### 2.1.3 Oportunidades de automação

A automação é mais apropriada em tarefas repetitivas, verificáveis e de baixo risco, como localização de informação institucional ou consulta a dados estruturados. O valor do sistema multiagente está em organizar essas funções e preservar uma rota de supervisão. O objetivo experimental, portanto, é medir como a estratégia de coordenação altera eficiência, observabilidade e qualidade operacional, sem avaliar aconselhamento clínico ou substituir profissionais.

## 2.2 INTELIGÊNCIA ARTIFICIAL NO ATENDIMENTO

### 2.2.1 Conceitos de inteligência artificial

A inteligência artificial compreende métodos computacionais capazes de executar tarefas que exigem percepção, inferência, aprendizagem, planejamento ou produção de linguagem. No escopo deste trabalho, o interesse não está em reproduzir toda a amplitude do campo, mas em compreender sistemas que recebem uma solicitação em linguagem natural, selecionam ações, consultam fontes externas e produzem uma resposta. Essa delimitação diferencia o protótipo de um chatbot baseado apenas em respostas pré-programadas: o comportamento depende do contexto, das ferramentas disponíveis e da estratégia de coordenação definida para os agentes.

### 2.2.2 IA aplicada ao atendimento ao cliente

Em operações de atendimento, a IA pode apoiar classificação de intenção, recuperação de informações, encaminhamento de demandas, composição de respostas e identificação de casos que exigem intervenção humana. A utilidade prática, entretanto, não deve ser avaliada somente pela fluência do texto. Um sistema de atendimento também precisa responder dentro de limites de tempo, acionar a ferramenta correta, preservar o contexto da conversa e encaminhar situações sensíveis. Por isso, o presente trabalho combina medidas de eficiência operacional com critérios de qualidade e segurança.

### 2.2.3 Uso de IA em saúde e farmácias

O uso de IA em saúde exige cautela adicional porque uma resposta inadequada pode afetar decisões individuais. O protótipo desenvolvido não realiza diagnóstico nem prescrição e não deve fornecer dosagens específicas. Seu domínio é o atendimento operacional de farmácia, incluindo perguntas frequentes, consulta de disponibilidade de produtos, processamento inicial de anexos e direcionamento para revisão profissional quando necessário. Essa fronteira funcional é coerente com a ampliação do papel das farmácias comunitárias, que passaram a oferecer serviços para além da dispensação de medicamentos, mantendo o farmacêutico como profissional responsável por orientações clínicas e uso seguro de medicamentos (WHO EUROPE, 2024).

## 2.3 LARGE LANGUAGE MODELS E AGENTES INTELIGENTES

### 2.3.1 Conceito de LLM

Large Language Models (LLMs) são modelos treinados em grandes coleções de texto para estimar e gerar sequências linguísticas. Quando empregados isoladamente, podem interpretar instruções e produzir respostas, mas não garantem, por si só, acesso a dados atualizados, execução de ações ou observância de regras de negócio. Essas capacidades adicionais dependem da arquitetura que envolve o modelo.

### 2.3.2 Uso de LLM em agentes

Um agente baseado em LLM associa o modelo a um objetivo, um conjunto de instruções, estado de execução e mecanismos de ação. O agente pode selecionar ferramentas, interpretar seus retornos e decidir como prosseguir. Li et al. (2024) organizam sistemas desse tipo em componentes como perfil, percepção, ação individual, interação e evolução. Essa visão é útil para separar a capacidade linguística do modelo das responsabilidades arquiteturais necessárias para operar um sistema completo.

### 2.3.3 Ferramentas e integração

Ferramentas conectam o agente a funções determinísticas ou serviços externos. No MAB, elas representam operações como consulta de perguntas frequentes, busca de estoque e análise inicial de anexos. A ferramenta devolve evidência estruturada; o agente decide quando acioná-la e como incorporar seu retorno. Essa separação melhora a observabilidade, pois chamadas, erros, tempo de execução e transições entre agentes podem ser registrados independentemente do texto final.

## 2.4 SISTEMAS MULTIAGENTES

### 2.4.1 Definição e características

Um sistema multiagente é formado por unidades computacionais que percebem informações, tomam decisões e atuam em um ambiente compartilhado, preservando algum grau de autonomia local. O comportamento global resulta da capacidade de cada agente e das regras que distribuem responsabilidades, informações e autoridade. Isso diferencia um sistema multiagente de uma aplicação que apenas realiza chamadas independentes a modelos: a colaboração exige uma estrutura comum de objetivos, comunicação e coordenação.

Nos sistemas baseados em *Large Language Models*, os agentes podem ser diferenciados por instruções, papéis, ferramentas, fontes de conhecimento e permissões. Um agente pode classificar a solicitação, outro recuperar evidências e um terceiro sintetizar a resposta. Li et al. (2024) descrevem elementos como perfil, percepção, ação, interação e evolução, evidenciando que o modelo é somente parte de uma organização mais ampla. A especialização facilita a decomposição, mas cria dependências: cada transferência exige preservar contexto e interpretar corretamente a saída anterior.

A quantidade de agentes, portanto, não mede sozinha a capacidade do sistema. Configurações com os mesmos agentes e modelos podem divergir por topologia, participação e compartilhamento de contexto. Qian et al. (2025) representam a colaboração por grafos acíclicos direcionados; Zhu et al. (2025) organizam protocolos em estrela, árvore, cadeia e grafo. Esses trabalhos sustentam uma distinção central: agentes são as unidades participantes; a arquitetura de coordenação define como elas formam um sistema.

### 2.4.2 Arquitetura de sistemas multiagentes

A arquitetura abrange a composição dos agentes e as relações que regulam sua atuação. Ela define quem inicia a execução, quais componentes acionam ferramentas, como o estado é mantido, quem autoriza transferências, quando o fluxo termina e qual unidade produz a resposta final. Portanto, não deve ser descrita apenas como um diagrama de módulos: ela contém decisões que condicionam o percurso de cada tarefa.

Revisões recentes mostram variações de topologia, autoridade, memória e controle (LI et al., 2024; PICCIALLI et al., 2025). Em uma organização hierárquica, um supervisor seleciona especialistas e consolida saídas. Em uma estrutura sequencial, o controle está incorporado à ordem das etapas. Em uma rede descentralizada, os agentes escolhem para qual par transferir a tarefa. Cada forma determina caminhos, pontos de falha e evidências diferentes para auditoria.

A topologia torna parte dessas diferenças observável. Uma estrela concentra comunicação em um nó; uma cadeia impõe ordem linear; uma árvore distribui subtarefas por níveis; e um grafo permite relações mais flexíveis (QIAN et al., 2025; ZHU et al., 2025). Contudo, grafos semelhantes podem adotar regras diferentes para participação, contexto, repetição e encerramento. A análise precisa combinar a forma da rede com os mecanismos de execução.

Em comparações experimentais, componentes alheios à variável arquitetural devem permanecer equivalentes. Modelo, ferramentas, cenários e critérios de avaliação precisam ser controlados para relacionar diferenças observadas à coordenação. No MAB, uma base funcional comum sustenta orquestração centralizada, *workflow* estruturado e *swarm* descentralizado. A farmácia fornece tarefas concretas, enquanto a arquitetura determina como os agentes organizam o trabalho.

### 2.4.3 Comunicação e coordenação entre agentes

A comunicação corresponde ao intercâmbio de solicitações, resultados, evidências e informações de controle. Ela pode ocorrer por mensagens diretas, estado compartilhado, chamadas mediadas ou *handoffs*, nos quais um agente transfere a continuidade para outro. Metadados como origem, destino, ferramenta, motivo da transferência e estado permitem reconstruir não apenas a resposta, mas o processo que a produziu.

Coordenação transforma essas interações em um fluxo coerente: estabelece participantes, autoridade sobre o próximo passo, resolução de conflitos e encerramento. Wang et al. (2025) organizam estratégias colaborativas em governança, participação, interação e gestão do histórico. Assim, coordenar não é apenas enviar mensagens, mas selecionar participantes e preservar o contexto necessário às decisões subsequentes.

O compartilhamento produz benefícios e custos. Evidências podem evitar trabalho duplicado, enquanto contexto incorreto pode propagar decisões inadequadas. Transferências excessivas elevam mensagens, tokens e latência. Hammond et al. (2025) incluem descoordenação, conflito e cooperação indesejada entre os riscos multiagentes. Mesmo com objetivo comum, podem ocorrer rotas incorretas, repetição, ciclos ou consolidação de evidência insuficiente.

Por isso, observabilidade e limites operacionais integram a coordenação. Identificadores, mensagens, ferramentas, transições, contagem de *handoffs* e condições de *timeout* permitem verificar o comportamento. A telemetria não elimina erros semânticos, mas torna comparáveis custos e caminhos. A seção seguinte distingue orquestração centralizada, *workflow* estruturado e *swarm* descentralizado sem pressupor superioridade antes das evidências experimentais.

## 2.5 ARQUITETURAS DE COORDENAÇÃO

### 2.5.1 Orquestração centralizada

Na orquestração centralizada, um supervisor concentra as decisões de classificação, seleção de ferramentas ou agentes e composição da resposta. A principal vantagem é a existência de um ponto claro de controle, que simplifica a aplicação de políticas e a reconstrução do fluxo. Como contrapartida, o supervisor pode se tornar gargalo e ponto único de falha. No MAB, a arquitetura centralizada utiliza um agente supervisor que escolhe entre ferramentas de FAQ, estoque e anexos e produz a resposta final.

### 2.5.2 Workflow estruturado

O workflow organiza a execução em etapas previamente definidas. No protótipo, o fluxo inclui classificação, coleta de evidência, análise multimodal quando aplicável, revisão e síntese. Cada etapa possui responsabilidade explícita e ordem estável. A previsibilidade facilita testes e auditoria, mas reduz a flexibilidade para alterar o caminho durante a execução. A revisão de Yu et al. (2025) mostra que workflows de agentes combinam planejamento, execução e controle em estruturas que variam de sequências fixas a fluxos adaptativos.

### 2.5.3 Sistemas descentralizados (swarm)

Em uma organização descentralizada, os agentes podem transferir a tarefa diretamente entre pares. O MAB implementa essa estratégia por meio de handoffs: um coordenador inicia a cadeia, especialistas podem delegar a outros especialistas e um sintetizador produz a resposta final. O mecanismo aumenta a autonomia local, porém exige limites de handoff e telemetria para evitar ciclos, custo excessivo ou perda de contexto.

### 2.5.4 Características e diferenças entre as arquiteturas

A comparação entre arquiteturas de coordenação não pode ser reduzida à quantidade de agentes empregados. Duas soluções com o mesmo número de agentes podem distribuir autoridade, estado e comunicação de maneiras distintas. Para analisá-las, é necessário observar pelo menos quatro dimensões: onde as decisões são concentradas; como o caminho de execução é definido; de que forma o contexto circula entre os agentes; e quais mecanismos permitem reconstruir ou interromper o fluxo. As taxonomias de Li et al. (2024) e Piccialli et al. (2025) mostram que interação, autonomia e organização são componentes próprios da arquitetura, e não apenas características do modelo de linguagem utilizado.

Wang et al. (2025) operacionalizam essa análise em quatro dimensões complementares: governança dos agentes, controle de participação, dinâmica de interação e gestão do histórico de diálogo. Em dois cenários dependentes de contexto, os autores relacionam essas escolhas tanto à acurácia da tarefa quanto à eficiência computacional. O estudo reforça que a comparação deve observar os mecanismos concretos de colaboração e circulação do contexto, e não somente o rótulo estrutural atribuído ao sistema.

Na orquestração centralizada, a autoridade de roteamento permanece em um supervisor. Esse componente recebe a solicitação, seleciona especialistas ou ferramentas e pode consolidar a resposta. A concentração favorece a aplicação uniforme de políticas e oferece um ponto explícito para registrar decisões. Em contrapartida, a execução fica condicionada à capacidade do supervisor de interpretar corretamente cada etapa. Um erro de classificação pode direcionar todo o fluxo para uma rota inadequada, enquanto o acúmulo de decisões em um único componente pode ampliar latência e dependência operacional. Assim, centralização significa maior controle global, mas também maior concentração de responsabilidade.

No workflow estruturado, parte do controle deixa de estar exclusivamente em um agente e passa a ser representada pela própria sequência de etapas. O fluxo pode definir antecipadamente operações de classificação, obtenção de evidências, revisão e síntese, incluindo condições para desvio ou encerramento. Yu et al. (2025) descrevem workflows de agentes como combinações de planejamento, execução e controle que podem variar entre sequências fixas e estruturas adaptativas. A explicitação das transições favorece repetibilidade e auditoria, pois torna possível identificar em qual etapa ocorreu uma falha. Entretanto, um caminho rígido pode executar operações desnecessárias ou responder de forma limitada a solicitações que não se ajustem às rotas previstas.

Em sistemas descentralizados, a decisão de continuidade pode ser transferida entre os próprios agentes. Em vez de consultar um supervisor a cada passo, um especialista avalia o contexto recebido e realiza um handoff quando identifica outra competência necessária. Balaprakash et al. (2025) apresentam o SWARM como uma proposta de distribuição das funções tradicionalmente centralizadas de gestão de workflows, motivada por problemas de resiliência e escalabilidade. Essa autonomia local pode reduzir a dependência de um único controlador, mas exige regras para preservar contexto, limitar transferências e impedir ciclos. Também pode aumentar a comunicação e a repetição de trabalho quando mais de um agente interpreta a mesma solicitação.

Esses benefícios e custos dependem do tipo de tarefa e da capacidade dos modelos envolvidos. Kim et al. (2026) compararam configurações de agente único, independentes, centralizadas, descentralizadas e híbridas em diferentes benchmarks. Os autores observaram que os ganhos da colaboração não são uniformes: tarefas decomponíveis podem se beneficiar da divisão de trabalho, enquanto tarefas que dependem de uma sequência rígida ou de coordenação intensa podem sofrer com o custo adicional de comunicação. O estudo também indica que modelos mais capazes podem reduzir a vantagem relativa da colaboração, pois parte do trabalho distribuído pode ser resolvida por um único agente sem os mesmos custos de coordenação.

Portanto, não existe fundamento para declarar previamente uma arquitetura como superior em qualquer contexto. Uma comparação controlada precisa manter constantes os elementos que não constituem o objeto do estudo, como cenários, ferramentas disponíveis, modelo de linguagem e critérios de avaliação. Em seguida, deve observar consequências mensuráveis da coordenação, como rota percorrida, quantidade de handoffs, chamadas de ferramentas, consumo de tokens, latência, ocorrência de erros e qualidade da resposta. Essa relação entre desenho arquitetural e eventos observáveis sustenta a comparação proposta pelo MAB, sem antecipar resultados: orquestração, workflow e swarm representam formas distintas de distribuir controle, e sua adequação ao atendimento farmacêutico deve ser determinada pelas evidências do experimento.
