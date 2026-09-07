# Verificação bibliográfica — 7 de setembro de 2026

Escopo: revisão integral da Fundamentação Teórica solicitada pelos autores. As quatro entradas abaixo foram registradas como candidatas antes da verificação e promovidas a `cited` após conferência e integração. Não foram utilizados resultados desses artigos como resultados do MAB.

| ID | Metadados confirmados | Uso e limite no Capítulo 2 | Fonte primária consultada |
|---|---|---|---|
| R064 | Eleni Adamopoulou; Lefteris Moussiades. An Overview of Chatbot Technology. AIAI 2020, IFIP AICT 584, p. 373–383. Publicação: 29 maio 2020. DOI 10.1007/978-3-030-49186-4_31. | 2.2: diversidade de interfaces e formas de construção de chatbots; não é evidência de superioridade de LLMs. | [Springer](https://link.springer.com/chapter/10.1007/978-3-030-49186-4_31) |
| R065 | Ashish Vaswani et al. Attention Is All You Need. Advances in Neural Information Processing Systems 30, 2017. | 2.3.1: atenção e relações na sequência; não implica que o modelo compreenda ou garanta a veracidade da resposta. | [NeurIPS](https://proceedings.neurips.cc/paper/2017/hash/3f5ee243547dee91fbd053c1c4a845aa-Abstract.html) |
| R066 | Tom B. Brown et al. Language Models are Few-Shot Learners. Advances in Neural Information Processing Systems 33, 2020. | 2.3.1: modelo autorregressivo e exemplos no contexto sem atualização de parâmetros a cada tarefa. | [NeurIPS](https://proceedings.neurips.cc/paper/2020/hash/1457c0d6bfcb4967418bfb8ac142f64a-Abstract.html) |
| R067 | Shunyu Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. ICLR 2023, Kigali, 1–5 maio 2023. | 2.3.2–2.3.3: alternância entre ações e observações; inspira esquema autoral, sem afirmar que o MAB implementa exatamente ReAct. | [Projeto dos autores](https://react-lm.github.io/), [Princeton](https://collaborate.princeton.edu/en/publications/react-synergizing-reasoning-and-acting-in-language-models/), [registro OpenReview](https://openreview.net/forum?id=WE_vluYUL-X) |

O OpenReview apresentou desafio de acesso nesta consulta; o método foi conferido na página dos autores e a publicação de 2023 no registro institucional de Princeton. O manuscrito não usa a data do preprint de 2022 como ano da publicação em conferência. As entradas completas, incluindo URLs e datas de acesso, foram acrescentadas à bibliografia do DOCX.

## Fontes já registradas reavaliadas

| ID | Papel mantido | Evidência consultada |
|---|---|---|
| R035 | Contexto dos serviços farmacêuticos, restrito a 2.1. | [WHO Europe](https://www.who.int/belgium/feature-stories/item/advancing-the-role-of-pharmacists-to-meet-changing-patient-and-health-system-needs) |
| R051 | Avaliação específica de instruções farmacêuticas, sem extrapolar para atendimento autônomo. | [Nature Medicine](https://www.nature.com/articles/s41591-024-02933-8) |
| R032 | Componentes e interação de agentes baseados em LLM. | [Vicinagearth](https://link.springer.com/article/10.1007/s44336-024-00009-2) |
| R034 | Revisão de organização de fluxos de agentes. | [IEEE, registro indexado](https://ieeexplore.ieee.org/document/11082076/), [manuscrito dos autores](https://arxiv.org/abs/2508.01186) |
| R038 | Benefício da colaboração condicionado a modelo e tarefa. | [Nature Machine Intelligence](https://www.nature.com/articles/s42256-026-01268-y) |
| R042 | Autoridade, participação, interação e histórico como dimensões distintas. | [ACL Anthology](https://aclanthology.org/2025.acl-long.1037/) |
| R057 | Topologias de comunicação; figura autoral sem atribuir um desenho a cada paper. | [ACL Anthology](https://aclanthology.org/2025.acl-long.421/) |
| R059 | Grafo computacional como objeto de projeto; distinção entre conectividade e percurso executado. | [PMLR](https://proceedings.mlr.press/v235/zhuge24a.html) |
| R004 | Riscos decorrentes das interações; identificado como relatório técnico/preprint. | [arXiv](https://arxiv.org/abs/2502.14143) |

R033 permanece citado na Introdução, mas foi retirado do Capítulo 2 por ser uma revisão ampla voltada à indústria 4.0. R044 e R041 continuam desenvolvidos no Capítulo 3; sua descrição não foi repetida na fundamentação. Nenhuma fonte comercial foi acrescentada ao Capítulo 2.

## Rastreabilidade da implementação

Leitura no commit-base `42b0ef1479a8979ffd302673346df026e8e5f2b5`: `apps/agent-runtime/app/architectures/centralized.py`, `workflow.py` e `swarm.py`. A configuração centralizada usa um agente com três ferramentas; o fluxo estruturado distribui etapas entre agentes, e o swarm admite transferências entre especialistas. A comparação dessas configurações não controla isoladamente o número de agentes. Essa limitação foi explicitada em 2.5.4 e na apresentação da figura de 6.3. O código foi apenas consultado.
