# Descoberta bibliográfica — 9 de setembro de 2026

## Escopo

A busca priorizou fontes acadêmicas primárias que ajudem a explicar e comparar mecanismos de coordenação em sistemas multiagentes baseados em LLMs. Foram procurados trabalhos sobre falhas de coordenação, custo comunicacional, distribuição de autoridade, segurança da delegação e roteamento centralizado ou descentralizado. O estudo de caso farmacêutico não foi usado como filtro principal, pois o objeto da pesquisa é a comparação arquitetural.

## Referências triadas

### R068 — Why Do Multi-Agent LLM Systems Fail?

- Fonte: anais oficiais da NeurIPS 2025, Datasets and Benchmarks Track; DOI <https://doi.org/10.52202/085713-4082>.
- Contribuição potencial: oferece uma taxonomia empírica de falhas ligada ao projeto do sistema, ao desalinhamento entre agentes e à verificação da tarefa.
- Uso possível: fortalecer 2.4.3 e 3.2–3.4, sobretudo na discussão sobre coordenação observável e critérios que vão além da qualidade final da resposta.
- Cautela: a rodada de verificação deve conferir quais frameworks, tarefas e modelos sustentam cada categoria antes de transportar a taxonomia para o MAB.

### R069 — United Minds or Isolated Agents? Exploring Coordination of LLMs under Cognitive Load Theory

- Fonte: arXiv:2506.06843v3, revisado em 21 de junho de 2026; <https://arxiv.org/abs/2506.06843>.
- Contribuição potencial: relaciona especialização, comunicação estruturada e memória coletiva à carga de coordenação; também delimita situações em que o custo da colaboração pode superar o benefício.
- Uso possível: aprofundar 2.4.3, 2.5 e 3.2–3.3 com uma explicação teórica para diferenças entre tarefas e estruturas de coordenação.
- Cautela: permanece registrado como preprint até a confirmação formal da situação editorial e do alcance do desenho experimental.

### R070 — MasDrift: Benchmarking Authorization Preservation Across Multi-Agent Architectures

- Fonte: arXiv:2608.07556v2, revisado em 11 de agosto de 2026; <https://arxiv.org/abs/2608.07556>.
- Contribuição potencial: trata a preservação de autorização durante a delegação como propriedade mensurável da arquitetura e compara configurações centralizadas e descentralizadas.
- Uso possível: apoiar 2.5, 3.2–3.4 e os controles de segurança de 4.11, sem substituir requisitos institucionais ou normativos.
- Cautela: é um preprint recente; resultados quantitativos não devem ser citados antes da conferência integral dos métodos, ameaças à validade e disponibilidade dos artefatos.

### R071 — Emergent Coordination in Multi-Agent Language Models

- Fonte: artigo publicado nos anais oficiais do ICLR 2026; <https://proceedings.iclr.cc/paper_files/paper/2026/file/c464fc4516aca4e68f2a14e67c6f0402-Paper-Conference.pdf>.
- Contribuição potencial: propõe medidas para distinguir sinergia entre agentes, redundância e acoplamento temporal sem contribuição para a tarefa.
- Uso possível: aprofundar 2.4.3 e 3.2–3.3 ao separar coordenação efetiva de mera troca de mensagens.
- Cautela: o próprio artigo delimita a análise a uma tarefa simples e não busca demonstrar superioridade geral sobre um agente isolado.

### R072 — DiSRouter: Distributed Self-Routing for LLM Selections

- Fonte: artigo publicado nos anais oficiais do ICLR 2026; <https://proceedings.iclr.cc/paper_files/paper/2026/file/e708577c4a0802320da036532281bc3b-Paper-Conference.pdf>.
- Contribuição potencial: contrapõe roteamento externo centralizado a decisões locais distribuídas e formula explicitamente o compromisso entre desempenho e custo.
- Uso possível: apoiar 2.5.1, 2.5.3 e 3.2–3.3 como comparação de distribuição de autoridade e roteamento.
- Cautela: a implementação avaliada usa principalmente uma cascata para seleção de modelos; não equivale diretamente ao swarm do MAB.

## Controle de duplicidade e decisão editorial

A busca também recuperou *Towards a Science of Scaling Agent Systems*. A entrada não foi adicionada porque o registro já contém R038, correspondente à versão publicada como *Capable language models can outgrow the benefits of collaboration*. Os cinco trabalhos acima não estavam presentes por título, DOI ou identificador.

Todas as novas entradas permanecem como `candidate`. Nenhuma citação foi adicionada ao manuscrito e nenhum resultado dos artigos foi incorporado ao texto. A promoção para `verified` ou `cited` depende da revisão formal de metadados, métodos, comparadores e limitações prevista para sexta-feira.
