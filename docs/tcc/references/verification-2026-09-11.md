# Verificação de referências — 11 de setembro de 2026

## Escopo

Foram verificadas R069–R072 nas fontes primárias. A avaliação considerou título, autoria, versão, tipo de publicação, método, limites e relação direta com a comparação de arquiteturas. A integração deu preferência aos artigos publicados em conferência.

## Decisões

### R069 — United Minds or Isolated Agents?

- Fonte: https://arxiv.org/abs/2506.06843
- Metadados: HaoYang Shang, Xuan Liu, Zi Liang, Jie Zhang, Haibo Hu e Song Guo; versão 3, revisada em 21 de junho de 2026.
- Situação: *preprint*.
- Escopo: propõe o CoThinker e relaciona especialização, comunicação estruturada e memória coletiva à carga de coordenação.
- Decisão: promovida a `verified`, sem citação. O argumento sobre custo e benefício da coordenação já possui apoio publicado mais direto no capítulo.

### R070 — MasDrift

- Fonte: https://arxiv.org/abs/2608.07556
- Metadados: Zhuoning Xu, Xiucheng Zhang, Hanjun Luo, Yingbin Jin, Yinpeng Dong e Hanan Salam; versão 2, revisada em 11 de agosto de 2026.
- Situação: *preprint*.
- Escopo: compara preservação de autorização em condições de agente único, coordenação centralizada e redes descentralizadas.
- Decisão: promovida a `verified`, sem citação. O tema é relevante, mas recente e ainda não revisado por pares; seus resultados não serão transportados ao MAB.

### R071 — Emergent Coordination in Multi-Agent Language Models

- Fonte: https://proceedings.iclr.cc/paper_files/paper/2026/file/c464fc4516aca4e68f2a14e67c6f0402-Paper-Conference.pdf
- Metadados: Christoph Riedl; artigo publicado na ICLR 2026.
- Escopo: utiliza decomposição parcial da informação para separar sinergia associada ao desempenho de acoplamento temporal espúrio.
- Limite: experimento restrito a um jogo de adivinhação sem comunicação direta entre agentes.
- Decisão: promovida a `cited` e integrada às seções 3.2 e 3.3 para sustentar a observação do processo de coordenação além do resultado final.

### R072 — DiSRouter

- Fonte: https://proceedings.iclr.cc/paper_files/paper/2026/file/e708577c4a0802320da036532281bc3b-Paper-Conference.pdf
- Metadados: Hang Zheng, Hongshen Xu, Yongkai Lin, Shuai Fan, Lu Chen e Kai Yu; artigo publicado na ICLR 2026.
- Escopo: substitui um roteador externo centralizado por políticas locais de decisão em uma cascata de modelos.
- Limite: os agentes usam modelos de tamanhos e custos diferentes e recebem treinamento específico de autoavaliação.
- Decisão: promovida a `cited` e integrada às seções 3.2 e 3.3 para caracterizar a distribuição da autoridade de roteamento, sem tratá-la como comparação equivalente às condições fixas do MAB.

## Resultado editorial

R069 e R070 permanecem como apoio verificado, sem ampliar a lista de citações com *preprints* redundantes. R071 e R072 acrescentam contribuições distintas e revisadas por pares ao Capítulo 3. Nenhuma afirmação de desempenho publicada foi transportada para a metodologia ou apresentada como resultado deste trabalho.
