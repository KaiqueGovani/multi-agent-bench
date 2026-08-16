# TCC — sistema multiagente para atendimento inteligente em farmácias

Esta pasta é a fonte versionada do TCC. O documento Word é a apresentação oficial para leitura e entrega; os arquivos Markdown, o registro de referências e o estado do ciclo são a base operacional do Ralph loop.

## Estado do projeto

- Protótipo implementado com três estratégias de coordenação: orquestração, workflow e swarm.
- Fase atual: preparação da coleta, anonimização e execução dos testes comparativos.
- Documento-base: `TCC_Base_MAB_Facens.docx`, mantido fora do repositório como artefato editável.
- Branch de operação: `agent/tcc-ralph-setup`.
- Um único pull request em modo draft deve concentrar os incrementos diários.

## Estrutura

- `manuscript/`: fonte textual por capítulo.
- `references/`: registro vivo, triagem e validação das referências.
- `state/`: estado persistente, backlog e histórico das execuções.
- `automation/`: prompt e calendário do agente diário.
- `format/`: regras de apresentação extraídas do manual da Facens.
- `data-governance.md`: limites para dados de WhatsApp e informações pessoais.

## Princípio de trabalho

Cada execução escolhe uma única ação pequena e de maior valor, produz evidência verificável, atualiza o estado e encerra. Nenhum resultado experimental pode ser inventado ou antecipado.
