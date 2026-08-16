# 6 DESENVOLVIMENTO DO SISTEMA

## 6.1 TECNOLOGIAS UTILIZADAS

O projeto utiliza uma stack dividida em backend transacional, frontend web e serviço de execução dos agentes. No backend, Python, FastAPI, Pydantic, SQLAlchemy, Alembic e PostgreSQL sustentam endpoints, validação e persistência. Server-Sent Events transmitem atualizações de processamento. Anexos podem ser armazenados localmente ou em serviço compatível com S3, com MinIO no ambiente local.

O frontend utiliza Next.js, React, TypeScript e Tailwind CSS. A interface reúne workspace de chat, histórico, anexos, timeline operacional, revisão humana, inspeção técnica, dashboard e visualização dos fluxos. Contratos compartilhados em TypeScript mantêm alinhados os objetos usados pelo frontend e pela API.

O runtime dos agentes utiliza Python, FastAPI, Strands Agents e AWS Bedrock quando o modo live está ativado. OpenTelemetry/OTLP pode exportar telemetria. O runtime também possui modo mock, empregado em testes determinísticos, no qual ferramentas e respostas controladas verificam contratos e sequências de eventos sem depender do modelo remoto.

## 6.2 IMPLEMENTAÇÃO DOS AGENTES

Os agentes compartilham um contexto de execução que oferece histórico recente da conversa, mensagem atual, anexos e ferramentas. O contexto mede chamadas, erros, loops, handoffs, tokens e tempos até eventos públicos. A seleção de rota considera três intenções implementadas: perguntas frequentes, consulta de estoque e processamento de anexos.

As ferramentas `faq_lookup`, `stock_lookup` e `attachment_intake` encapsulam a lógica de domínio. No modo live, hooks registram o início e o término de cada chamada. Se a invocação do modelo falha ou não está habilitada, o runtime utiliza respostas mock explicitamente identificadas, evitando apresentar a simulação como execução real.

## 6.3 IMPLEMENTAÇÃO DAS ARQUITETURAS

Na orquestração centralizada, um único supervisor recebe a mensagem e dispõe das três ferramentas. O prompt do supervisor define as regras de roteamento e exige encaminhamento profissional para perguntas clínicas. Depois de usar uma ferramenta, o mesmo agente compõe a resposta final. O fluxo não realiza handoffs entre pares.

O workflow estruturado implementa um pipeline com agentes diferentes para classificação, coleta de evidência, revisão e síntese. Se houver anexo, a rota de análise de imagem é priorizada. O agente de revisão decide se a resposta exige intervenção humana com base em categorias de risco, e o sintetizador recebe evidência e decisão de revisão antes de produzir o texto final.

O swarm descentralizado utiliza uma ferramenta de handoff. Um coordenador delega a solicitação para especialistas de FAQ, estoque ou anexos; esses especialistas podem transferir a tarefa a outro par quando precisam de informação complementar. Um limite configurável impede transferências indefinidas. Um sintetizador é acionado quando o retorno do coordenador não constitui uma resposta final adequada. Cada transferência incrementa contadores de handoff e loop.

## 6.4 INTEGRAÇÃO COM FERRAMENTAS

A API cria e acompanha runs, despacha a execução ao runtime e persiste o desfecho. Eventos técnicos descrevem nós, mensagens, ferramentas e handoffs, permitindo alimentar a timeline da interface e os relatórios comparativos. O benchmark existente executa os mesmos cenários contra as três arquiteturas e agrega sucesso, latência p50/p95, tokens, chamadas de ferramenta, erros, loops, handoffs e revisão humana.

Os testes utilizam Pytest no backend e no runtime, Playwright no frontend e cenários declarativos em YAML para validação E2E. O framework atual verifica rota, eventos, termos esperados, termos proibidos e timeout. A avaliação semântica das respostas em modo live permanece pendente da definição metodológica registrada na OQ-002; portanto, ela não é tratada como resultado implementado.
