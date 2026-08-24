# Prompt da tarefa diária — Ralph loop do TCC

Trabalhe no TCC “Sistema multiagente para atendimento inteligente em farmácias: uma análise comparativa de arquiteturas de coordenação”. Use o repositório `KaiqueGovani/multi-agent-bench` como fonte técnica e a versão Word `TCC_Base_MAB_Facens.docx` como artefato de apresentação.

## Objetivo de cada execução

Realizar apenas a próxima ação pequena de maior valor para aproximar o TCC de uma versão final correta, verificável e formatada. O protótipo já foi implementado; a fase atual é preparação/coleta dos dados e execução dos testes.

## Procedimento obrigatório

1. Abra o repositório e leia `docs/tcc/AGENTS.md`, `docs/tcc/state/ralph-state.yml`, `docs/tcc/state/evidence-gates.yml`, `docs/tcc/open-questions/questions.yml`, `docs/tcc/open-questions/README.md`, `docs/tcc/automation/focus-calendar.md` e `docs/tcc/data-governance.md`.
2. Verifique as GitHub Issues abertas com o prefixo `[TCC][Open Question]`. Se houver resposta humana ainda não integrada e ela permitir uma ação completa, incorpore-a, registre a decisão e encerre a questão antes de criar outra.
3. Reavalie o backlog documental, considerando o foco do dia. Consulte o código-fonte somente em modo leitura quando for indispensável para verificar uma descrição técnica.
4. Escolha uma única ação delimitada. Exemplos: concluir uma subseção; verificar cinco referências; formalizar uma métrica; corrigir uma divergência código–texto; revisar formatação de um capítulo.
5. Execute e grave a ação diretamente na branch dedicada `agent/tcc-ralph-setup`. Não abra, reutilize ou dependa de pull requests.
6. Se o trabalho alterar texto do manuscrito, reflita a mudança no DOCX. Execute integralmente o pipeline de duas passagens de `docs/tcc/format/README.md`, preserve `docs/tcc/format/facens-rules.md` e nunca digite a numeração dos títulos manualmente. Título 1, Título 2 e Título 3 devem usar os níveis decimais `1`, `1.1` e `1.1.1` da mesma lista multinível e do mesmo `numId`; bullets, estilos sem `numPr` ou listas diferentes devem interromper a compilação. No sumário, use tab stop automático à direita com líder pontilhado; nunca simule o preenchimento com sequências de `.`.
7. Valide o resultado: referências e URLs verificáveis, afirmações apoiadas, alinhamento com o código, ausência de dados pessoais e auditoria estrutural do DOCX. A auditoria deve confirmar uma lista multinível decimal única, os três estilos de título vinculados aos níveis corretos do mesmo `numId` e ausência de bullets ou numeração manual. A auditoria do sumário deve confirmar `w:tab w:val="right" w:leader="dot"`, um elemento `w:tab` entre título e página, ausência de pontos literais usados como líder e alinhamento uniforme dos números. Renderize e inspecione visualmente todas as páginas; confirme numeração de capítulos e subseções, sumário, paginação, referências e `et al.` em itálico, inclusive em tabelas.
8. Atualize `docs/tcc/state/ralph-state.yml` e crie um registro único em `docs/tcc/state/runs/` com ação, evidência, arquivos alterados, riscos e próxima sugestão. Para várias execuções no mesmo dia, use sufixo sequencial.
9. Produza um resumo curto do que mudou, das Open Questions pendentes e do que precisa de decisão humana.

## Quarta e sexta

- Quarta: faça uma busca nova em fontes confiáveis, preferencialmente IEEE Xplore, ACM Digital Library, Springer, ScienceDirect, Scopus/Web of Science quando acessíveis, PubMed para o contexto de saúde, arXiv apenas como preprint claramente identificado e documentação primária para detalhes de implementação.
- Sexta: valide e integre. Verifique título, autores, ano, DOI/URL, tipo de publicação e relação direta com uma seção. Substitua referências fracas ou irrelevantes antes de apenas aumentar a lista.
- Toda fonte começa como `candidate`. Só promova para `verified` após abrir a fonte primária e conferir os metadados. Só promova para `cited` após inserir uma citação sustentando uma afirmação específica.

## Restrições

- Nunca invente resultados, autores, DOI, citações ou detalhes de implementação.
- Os capítulos 7 — Experimentos e Resultados, 8 — Discussão e 9 — Considerações Finais estão protegidos pelos gates de `docs/tcc/state/evidence-gates.yml`. Enquanto um gate estiver `closed`, mantenha apenas títulos, subtítulos e placeholders explícitos; não redija resultados preliminares, interpretações, conclusões, contribuições confirmadas ou trabalhos futuros apresentados como decorrentes dos experimentos.
- Nem dados preliminares nem arquivos parciais abrem um gate. O agente não pode alterar o status de um gate. Somente uma autorização humana explícita dos autores, após a verificação das evidências, permite a abertura.
- Se a ação mais prioritária exigir um capítulo bloqueado, registre a dependência e selecione a próxima ação permitida.
- Abra uma Open Question somente quando a resposta humana alterar materialmente o texto, o método ou uma decisão do projeto. A pergunta deve conter contexto, seção afetada, alternativas, recomendação do agente, impacto da decisão e uma forma simples de resposta.
- Use o identificador sequencial `OQ-NNN`, registre-o em `docs/tcc/open-questions/questions.yml` e abra uma Issue intitulada `[TCC][Open Question][OQ-NNN] pergunta curta`. Crie no máximo uma por execução e nunca ultrapasse cinco questões ativas.
- Antes de perguntar, procure a resposta no repositório, nos documentos e em fontes confiáveis. Não transfira ao humano uma pesquisa que o agente pode realizar sozinho.
- Quando houver resposta, registre um resumo fiel, a autoria, a data e os arquivos/seções alterados. Depois marque a questão como `integrated` e encerre a Issue com um comentário de rastreabilidade.
- Não inclua dados pessoais, conteúdo bruto do WhatsApp ou segredos nas perguntas ou respostas registradas.
- Uma resposta humana não substitui uma citação verificável e não autoriza abrir um evidence gate.
- Nunca copie dados brutos de WhatsApp para o GitHub ou para o texto.
- Não altere código-fonte, testes, infraestrutura ou configuração do protótipo. O escopo da tarefa é exclusivamente o documento do TCC e seus artefatos editoriais. Se houver divergência entre texto e implementação, corrija o texto ou registre uma pendência documental.
- Não faça mudanças amplas. Se a ação não couber em uma revisão curta, divida e execute apenas a primeira parte completa.
- Se faltar acesso, evidência ou decisão do orientador, registre um bloqueio e encerre sem improvisar.
