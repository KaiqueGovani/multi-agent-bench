# Prompt da tarefa diária — Ralph loop do TCC

Trabalhe no TCC “Sistema multiagente para atendimento inteligente em farmácias: uma análise comparativa de arquiteturas de coordenação”. Use o repositório `KaiqueGovani/multi-agent-bench` como fonte técnica e a versão Word `TCC_Base_MAB_Facens.docx` como artefato de apresentação.

## Objetivo de cada execução

Realizar apenas a próxima ação pequena de maior valor para aproximar o TCC de uma versão final correta, verificável e formatada. O protótipo já foi implementado; a fase atual é preparação/coleta dos dados e execução dos testes.

## Procedimento obrigatório

1. Abra o repositório e leia `docs/tcc/AGENTS.md`, `docs/tcc/state/ralph-state.yml`, `docs/tcc/automation/focus-calendar.md` e `docs/tcc/data-governance.md`.
2. Inspecione as alterações recentes do código e do TCC. Reavalie o backlog, considerando o foco do dia.
3. Escolha uma única ação delimitada. Exemplos: concluir uma subseção; verificar cinco referências; formalizar uma métrica; corrigir uma divergência código–texto; revisar formatação de um capítulo.
4. Execute a ação na branch `agent/tcc-ralph-setup`. Reutilize o pull request draft nº 3; não abra um PR novo por dia.
5. Se o trabalho alterar texto do manuscrito, reflita a mudança no DOCX. Preserve as regras Facens registradas em `docs/tcc/format/facens-rules.md`.
6. Valide o resultado: referências e URLs verificáveis, afirmações apoiadas, alinhamento com o código, formatação e ausência de dados pessoais.
7. Atualize `docs/tcc/state/ralph-state.yml` e crie `docs/tcc/state/runs/AAAA-MM-DD.md` com ação, evidência, arquivos alterados, riscos e próxima sugestão.
8. Produza um resumo curto do que mudou e do que precisa de decisão humana.

## Quarta e sexta

- Quarta: faça uma busca nova em fontes confiáveis, preferencialmente IEEE Xplore, ACM Digital Library, Springer, ScienceDirect, Scopus/Web of Science quando acessíveis, PubMed para o contexto de saúde, arXiv apenas como preprint claramente identificado e documentação primária para detalhes de implementação.
- Sexta: valide e integre. Verifique título, autores, ano, DOI/URL, tipo de publicação e relação direta com uma seção. Substitua referências fracas ou irrelevantes antes de apenas aumentar a lista.
- Toda fonte começa como `candidate`. Só promova para `verified` após abrir a fonte primária e conferir os metadados. Só promova para `cited` após inserir uma citação sustentando uma afirmação específica.

## Restrições

- Nunca invente resultados, autores, DOI, citações ou detalhes de implementação.
- Nunca copie dados brutos de WhatsApp para o GitHub ou para o texto.
- Não altere código do protótipo salvo quando a tarefa do TCC exigir uma correção documental mínima e explicitamente segura; prefira registrar a divergência.
- Não faça mudanças amplas. Se a ação não couber em uma revisão curta, divida e execute apenas a primeira parte completa.
- Se faltar acesso, evidência ou decisão do orientador, registre um bloqueio e encerre sem improvisar.
