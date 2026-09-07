# 2 FUNDAMENTAÇÃO TEÓRICA

Este capítulo apresenta os conceitos necessários para comparar arquiteturas de coordenação em sistemas baseados em modelos de linguagem. O atendimento em farmácias delimita o estudo de caso. Em seguida, são discutidos os sistemas conversacionais, o funcionamento dos agentes e as formas de organizar sua execução.

## 2.1 ATENDIMENTO EM FARMÁCIAS

O atendimento em farmácias reúne atividades comerciais, administrativas e de orientação em saúde. A atuação do farmacêutico vai além da dispensação de medicamentos e inclui o apoio ao uso seguro desses produtos, conforme o contexto dos serviços prestados (WHO EUROPE, 2024). Para a automação, essa diversidade exige distinguir solicitações que podem ser resolvidas por consulta a informações de situações que dependem de avaliação profissional.

Uma pergunta sobre horário de funcionamento pode ser respondida a partir de informação institucional. Uma consulta de disponibilidade exige acesso a uma fonte de estoque. Já uma dúvida sobre dose ou interação entre medicamentos envolve uma decisão de saúde. Neste trabalho, essas situações ilustram diferentes necessidades de informação e encaminhamento; não constituem categorias observadas em conversas reais, cuja caracterização ainda está prevista na metodologia.

O estudo de Pais et al. (2024), sobre identificação de erros em instruções de medicamentos em farmácias digitais, mostra a pertinência de avaliar modelos em tarefas farmacêuticas específicas. Seu escopo, porém, não equivale à validação de um atendente autônomo para qualquer solicitação de saúde. Para o estudo de caso do MAB, a automação foi delimitada a funções operacionais e ao encaminhamento para revisão profissional. Essa delimitação permite investigar a coordenação sem assumir capacidade de diagnóstico ou prescrição.

A farmácia oferece, portanto, um contexto para tarefas com diferentes fontes de informação e graus de sensibilidade. O objeto da comparação continua sendo a organização computacional dessas tarefas. A eventual aplicação das conclusões a outros setores dependerá de estudos adicionais.

## 2.2 INTELIGÊNCIA ARTIFICIAL NO ATENDIMENTO

No atendimento, o processamento de linguagem natural permite associar mensagens a intenções, recuperar informações e produzir respostas. A revisão de Adamopoulou e Moussiades (2020) descreve sistemas conversacionais em diferentes áreas e distingue suas finalidades e formas de construção. Essa variedade é relevante porque a presença de uma interface de conversa não determina como o sistema obtém a resposta.

Um *chatbot* pode operar por regras, recuperar uma resposta de uma base ou utilizar um modelo generativo. Também pode oferecer acesso a funções executadas por um ou mais agentes. Assim, interface conversacional, modelo de linguagem e agente designam componentes diferentes. A escolha entre essas soluções depende das ações necessárias, das fontes disponíveis e dos limites impostos ao atendimento.

Neste estudo, a qualidade do atendimento automatizado inclui a adequação à solicitação, a correção das informações e o encaminhamento quando a resposta depende de avaliação humana. O tempo de resposta e o consumo de recursos compõem outra dimensão. Esses critérios precisam ser examinados em conjunto: uma resposta fluente pode conter informação incorreta, e uma execução tecnicamente concluída pode não atender à necessidade do usuário. A avaliação de Pais et al. (2024) reforça a importância de critérios próprios da tarefa, sobretudo quando o conteúdo envolve medicamentos.

## 2.3 MODELOS DE LINGUAGEM E AGENTES INTELIGENTES

### 2.3.1 Modelos de linguagem de grande porte

Modelos de linguagem de grande porte, conhecidos pela sigla LLM, de *Large Language Model*, aprendem regularidades em grandes coleções de texto. Em um modelo autorregressivo, a geração ocorre pela previsão do próximo *token* a partir dos anteriores. Um *token* é uma unidade de representação textual que pode corresponder a uma palavra, parte dela ou sinal de pontuação. Brown et al. (2020) demonstram o uso de instruções e exemplos no próprio contexto de entrada para orientar tarefas sem atualizar os parâmetros do modelo a cada solicitação.

A arquitetura *Transformer*, apresentada por Vaswani et al. (2017), utiliza mecanismos de atenção para relacionar elementos da sequência. Esse fundamento ajuda a compreender por que o contexto fornecido ao modelo influencia a resposta: diferentes partes da entrada participam do cálculo das representações usadas na geração.

Os parâmetros aprendidos durante o treinamento são distintos do contexto fornecido na execução. Histórico de conversa, instruções e resultados de consultas podem ser incluídos nesse contexto sem representar novo treinamento. O acesso a informações atuais, como disponibilidade de produtos, exige uma fonte externa ao conhecimento aprendido. Por isso, a geração de texto precisa ser integrada às funções do sistema de atendimento.

### 2.3.2 Agentes baseados em LLM

Um agente baseado em LLM combina o modelo com instruções, informações sobre a tarefa e meios de agir no ambiente. Ele utiliza as informações recebidas para selecionar uma ação, observar seu resultado e decidir como continuar. A revisão de Li et al. (2024) descreve componentes como perfil, percepção, ação e interação, situando o modelo dentro de uma estrutura de execução mais ampla.

Yao et al. (2023) apresentam o método ReAct, que intercala raciocínio textual, ações e observações do ambiente. O interesse desse método para a fundamentação está no ciclo de execução: uma consulta externa pode fornecer informação para a decisão seguinte, em vez de toda a resposta depender apenas da entrada inicial. Isso não significa que todo agente deva reproduzir exatamente esse método.

A figura a seguir representa uma forma simplificada desse ciclo. A aplicação executa a chamada de ferramenta solicitada pelo modelo, incorpora o retorno ao contexto e pode realizar uma nova consulta ao LLM. O ciclo termina quando há uma resposta ou quando uma condição de encerramento é atingida. Limites de tempo e de chamadas são controles da aplicação, não garantias fornecidas pela linguagem do modelo.

<!-- FIGURE: IMG-C020 | caption: Ciclo de execução de um agente com ferramentas. -->
![Entrada de contexto no LLM, seleção de ação, execução de ferramenta, retorno da observação e produção de resposta.](../figures/original/insertion-map-2026-09-02/02-anatomia-agente-llm.svg)

Fonte: elaboração própria (2026), com base em Yao et al. (2023).

### 2.3.3 Ferramentas, contexto e limites de execução

Uma ferramenta é uma função que a aplicação disponibiliza ao agente, como consulta a uma base, cálculo ou acesso a um serviço. Sua descrição informa a finalidade e os argumentos esperados. O modelo pode solicitar a chamada, mas a execução ocorre no programa que o envolve. O retorno deve ser distinguido do texto gerado pelo LLM: pode conter um valor encontrado, ausência de dados ou erro de execução.

Por exemplo, em uma consulta de estoque, o sistema precisa identificar o produto, executar a busca e interpretar o retorno antes de compor a resposta. Se o produto não for localizado, isso deve permanecer explícito. A conexão a ferramentas amplia as ações possíveis, mas também acrescenta falhas de integração e exige tratamento de argumentos, permissões e erros. Esses controles pertencem ao projeto do sistema.

O contexto de execução registra as informações necessárias para continuar a tarefa. Ele não precisa conter todo o histórico disponível, nem implica memória permanente. A seleção do que cada agente recebe torna-se especialmente importante quando vários agentes participam da mesma solicitação, como discutido a seguir.

## 2.4 SISTEMAS MULTIAGENTES

### 2.4.1 Agentes e divisão de responsabilidades

Um sistema multiagente reúne agentes que interagem em um ambiente. Eles podem cooperar, competir ou combinar essas relações. Neste trabalho, o recorte é cooperativo: diferentes agentes participam da resolução de uma solicitação. A especialização pode ser definida por instruções, ferramentas e informações acessíveis, mesmo quando os participantes utilizam o mesmo modelo de linguagem (LI et al., 2024).

Separar responsabilidades permite distribuir tarefas, como recuperar informação, revisar uma resposta e produzir sua versão final. Contudo, essa divisão cria dependências: um agente precisa receber dados suficientes e interpretar corretamente o trabalho anterior. A revisão de Li et al. (2024) trata a interação como componente próprio do sistema, o que justifica analisar a colaboração além das capacidades individuais.

A participação de mais agentes não garante melhor desempenho. Kim et al. (2026) investigam condições em que a capacidade do modelo e as características da tarefa alteram os benefícios da colaboração. Para este TCC, essa evidência fundamenta a necessidade de avaliar o custo da divisão de trabalho, em vez de considerar a quantidade de agentes como medida de qualidade.

### 2.4.2 Topologia e distribuição de controle

A topologia descreve as conexões possíveis entre os participantes. Na estrela, os demais nós se ligam a um centro; na cadeia, as conexões formam uma sequência; na árvore, os nós se organizam em ramificações. Outras redes permitem conexões adicionais entre pares. Zhu et al. (2025) incluem essas formas em sua avaliação de protocolos multiagentes. A figura seguinte apresenta apenas exemplos conceituais das conexões.

<!-- FIGURE: IMG-C022 | caption: Exemplos de topologias de comunicação entre agentes. -->
![Quatro redes com nós e conexões: estrela, cadeia, árvore e rede com conexões adicionais entre pares.](../figures/original/insertion-map-2026-09-02/04-topologias-trabalhos-correlatos.svg)

Fonte: elaboração própria (2026), com base em Zhu et al. (2025).

A topologia, isoladamente, não informa quem decide a próxima ação, qual conteúdo é transmitido ou quando a tarefa termina. H. Wang et al. (2025) distinguem organização da autoridade, controle de participação, dinâmica das interações e gestão do histórico. Essas dimensões ajudam a descrever as regras de execução que um desenho de conexões não revela.

Também é necessário separar estrutura permitida de percurso executado. Uma rede pode admitir várias conexões, embora uma solicitação utilize apenas parte delas. Zhuge et al. (2024) representam agentes e fluxos de informação por grafos computacionais, mostrando que a conectividade pode ser objeto de projeto e otimização. Nesta pesquisa, o interesse está em comparar configurações previamente definidas e observar os percursos que elas produzem.

### 2.4.3 Comunicação, coordenação e observabilidade

Comunicação é a troca de informações entre agentes. Coordenação é o conjunto de regras que organiza sua atuação: quem participa, quem recebe a tarefa, como se combinam as respostas e quais condições encerram a execução. Uma transferência de tarefa, ou *handoff*, envolve a passagem da continuidade do processamento; uma mensagem, por sua vez, pode apenas fornecer informação a outro participante.

O conteúdo compartilhado pode incluir a solicitação, resultados de ferramentas e partes do histórico. Enviar informação insuficiente pode comprometer a decisão seguinte; repetir todo o contexto em cada interação pode aumentar o consumo de *tokens*. H. Wang et al. (2025) incluem a gestão do histórico entre os mecanismos que relacionam qualidade e eficiência da colaboração.

As interações também podem propagar erros ou produzir conflitos. Hammond et al. (2025), em relatório técnico disponibilizado como *preprint*, sistematizam riscos de descoordenação, conflito e cooperação indesejada. Essa classificação não demonstra que todos esses riscos ocorram no MAB; ela fornece uma base para examinar falhas que surgem da interação entre agentes.

A observabilidade permite reconstruir a execução a partir de registros de chamadas, retornos, transferências, erros e tempos. Esses registros ajudam a localizar onde o processamento falhou, mas não comprovam que o conteúdo da resposta esteja correto. Por isso, a avaliação precisa relacionar o percurso técnico com critérios de qualidade da tarefa.

## 2.5 ARQUITETURAS DE COORDENAÇÃO

### 2.5.1 Orquestração centralizada

Na orquestração centralizada, um controlador concentra as decisões sobre o encaminhamento das tarefas e a composição da resposta. Ele pode acionar outros agentes ou utilizar ferramentas diretamente. A característica que define a centralização é a autoridade sobre o fluxo, e não a existência obrigatória de vários especialistas. A dimensão de organização da autoridade discutida por H. Wang et al. (2025) sustenta essa distinção.

Um ponto de decisão explícito facilita identificar a origem do encaminhamento e aplicar regras comuns. Ao mesmo tempo, uma escolha incorreta do controlador pode comprometer as etapas seguintes. O efeito sobre latência e custo depende das chamadas realizadas; não decorre automaticamente do rótulo “centralizado”.

### 2.5.2 Fluxo estruturado (workflow)

Um *workflow* organiza o processamento por etapas e transições definidas na aplicação. Cada etapa pode utilizar um agente, uma ferramenta ou uma regra determinística. A passagem entre etapas pode ser sequencial ou condicional. Assim, um fluxo estruturado não precisa executar sempre o mesmo caminho, mas suas alternativas são estabelecidas no projeto. Yu et al. (2025) revisam diferentes formas de organização de fluxos de agentes.

A explicitação das transições favorece a identificação da etapa responsável por uma saída e permite definir pontos de validação. A limitação está na cobertura das rotas previstas: solicitações que exigem outra sequência podem depender de uma nova regra. A execução de etapas desnecessárias também pode acrescentar tempo e chamadas ao modelo.

### 2.5.3 Coordenação descentralizada (swarm)

Na coordenação descentralizada, agentes podem decidir a continuidade do trabalho e transferir tarefas entre pares. O termo *swarm* é utilizado neste estudo para essa forma de delegação. A existência de um agente que inicia a solicitação não elimina a descentralização das decisões posteriores. Também não implica que todos os agentes estejam conectados entre si ou executem em paralelo.

Essa organização permite solicitar outra competência durante a execução, mas exige regras para identificar o destinatário, transmitir contexto e encerrar transferências. Em termos conceituais, topologia e autonomia precisam ser analisadas separadamente, como indicam as dimensões de interação de Li et al. (2024). A ausência de um supervisor em cada etapa não dispensa controle de erros nem acompanhamento do fluxo.

### 2.5.4 Síntese da comparação

A figura a seguir resume onde o controle é exercido nas três organizações. Os desenhos são esquemas conceituais: representam possibilidades de coordenação, e não medições ou a sequência exata de uma execução do MAB.

<!-- FIGURE: IMG-C019 | caption: Distribuição de controle nas três arquiteturas de coordenação. -->
![Supervisor central ligado a agentes, etapas ordenadas por regras e transferências entre agentes sem supervisor em cada passo.](../figures/original/insertion-map-2026-09-02/01-comparacao-arquiteturas.svg)

Fonte: elaboração própria (2026), com base em Li et al. (2024), Yu et al. (2025) e H. Wang et al. (2025).

As três organizações diferem principalmente pela autoridade sobre o próximo passo e pela definição das transições. Entretanto, o custo depende do percurso realmente executado, das chamadas ao modelo e do contexto transmitido. A comparação deve considerar essas decisões em conjunto com a qualidade das respostas, conforme a análise dos mecanismos de colaboração de H. Wang et al. (2025).

No MAB, a configuração centralizada utiliza um único agente com ferramentas; o fluxo estruturado e o *swarm* distribuem responsabilidades entre agentes, conforme descrito no Capítulo 6. Portanto, o experimento compara configurações completas de coordenação com funções de domínio comuns, e não apenas topologias com igual número de agentes. Essa diferença deve ser considerada na interpretação dos resultados, sem atribuir todo efeito exclusivamente ao formato das conexões. O capítulo seguinte apresenta os trabalhos que orientam esse recorte comparativo.
