# 5 MODELAGEM DA SOLUÇÃO

## 5.1 VISÃO GERAL DO SISTEMA

O MAB foi modelado para comparar estratégias de coordenação sem alterar o domínio, as ferramentas ou o formato de entrada. O sistema recebe mensagens de atendimento, persiste a conversa, cria uma execução identificada como run e encaminha a solicitação ao serviço responsável pelos agentes. A arquitetura selecionada processa o mesmo contrato de entrada e devolve, além do texto final, eventos que descrevem decisões, ferramentas, transferências e necessidade de revisão.

A separação entre canal, API e runtime permite que uma mensagem proveniente da interface web ou de uma integração futura seja normalizada antes de chegar aos agentes. Essa decisão evita acoplar as arquiteturas ao WhatsApp e mantém o experimento centrado no mecanismo de coordenação.

## 5.2 ARQUITETURA PROPOSTA

A solução é organizada em três camadas. A camada de interação recebe mensagens e exibe respostas, eventos e painéis de acompanhamento. A API transacional gerencia conversas, mensagens, anexos, runs e persistência. O runtime dos agentes implementa uma interface comum de execução e registra as arquiteturas `centralized_orchestration`, `structured_workflow` e `decentralized_swarm`.

Todas as estratégias recebem o mesmo objeto de requisição, que inclui a mensagem atual, histórico recente, anexos e metadados. O contexto de execução concentra emissão de eventos, contagem de tokens, chamadas de ferramentas, loops, handoffs e tempo decorrido. Essa interface comum é essencial para a validade interna da comparação, pois reduz diferenças que não pertencem à arquitetura avaliada.

## 5.3 COMPONENTES DO SISTEMA

O supervisor da arquitetura centralizada classifica a mensagem, escolhe entre FAQ, estoque e análise de anexos e compõe a resposta. No workflow, agentes especializados executam estágios ordenados de classificação, coleta de evidência, revisão e síntese. No swarm, um coordenador inicia a delegação; especialistas de FAQ, estoque e anexos podem realizar handoffs entre pares; e um sintetizador produz a saída final quando necessário.

As ferramentas de domínio são funções separadas dos agentes. Elas retornam dados de FAQ, disponibilidade simulada e informações iniciais sobre anexos. A revisão humana é representada por um indicador explícito na run. A telemetria utiliza eventos de início, conclusão e falha para nós, ferramentas, mensagens e handoffs, permitindo reconstruir o caminho de cada execução.

O armazenamento relacional preserva conversas, mensagens e runs, enquanto anexos podem ser mantidos em armazenamento local ou compatível com S3. Contratos compartilhados reduzem divergências entre frontend, API e runtime. Nenhum desses componentes autoriza armazenamento de conversas reais do WhatsApp no repositório público.

## 5.4 FLUXO DE ATENDIMENTO

O fluxo inicia com a normalização da mensagem e a seleção da arquitetura pelos metadados da conversa ou da run. Em seguida, a API despacha a solicitação ao runtime e publica eventos de processamento. A arquitetura interpreta o contexto, aciona ferramentas e produz a resposta. Quando identifica conteúdo clínico, insuficiência de evidência ou outro critério de risco, a execução é marcada para revisão humana.

Na arquitetura centralizada, as decisões passam por um supervisor. No workflow, cada etapa só começa depois da anterior, com responsabilidades previsíveis. No swarm, as transferências são registradas como handoffs e limitadas por configuração. Ao final, o runtime devolve texto, desfecho, contagens e identificador de trace; a API persiste o resultado e a interface atualiza o atendimento por eventos enviados ao cliente.
