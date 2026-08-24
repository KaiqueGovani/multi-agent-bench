# Regras de formatação Facens para o TCC

Consolidação baseada no modelo Word e nos manuais técnicos fornecidos pelos autores. Em caso de conflito, prevalece a orientação institucional mais recente confirmada pelos autores.

## Página e texto corrido

- papel A4;
- margens superior e esquerda de 3 cm; inferior e direita de 2 cm;
- Arial 12;
- alinhamento justificado;
- espaçamento 1,5;
- recuo de primeira linha de 1,25 cm;
- sem espaço adicional antes ou depois dos parágrafos corridos.

## Seções numeradas

- usar numeração progressiva decimal, sem ponto depois do último número;
- capítulo (nível 1): Arial 14, negrito, caixa alta, alinhado à esquerda e iniciado em nova página;
- seção (nível 2): Arial 12, negrito, caixa alta e alinhada à esquerda;
- subseção (nível 3 ou superior): Arial 12, sem negrito, caixa alta e alinhada à esquerda;
- todos os títulos devem usar preto absoluto (`#000000`), sem cores de tema ou destaque azul herdado;
- manter uma linha e meia de separação antes e depois de cada título; entre títulos consecutivos, usar apenas um intervalo;
- toda numeração deve ser gerada por uma única lista multinível vinculada aos estilos de título; números digitados manualmente no texto do título são proibidos.
- a lista deve usar exclusivamente o formato decimal nos três níveis: nível 1 `%1` (`1`), nível 2 `%1.%2` (`1.1`) e nível 3 `%1.%2.%3` (`1.1.1`), sem ponto depois do último algarismo;
- o marcador numérico deve declarar Arial nos quatro atributos OOXML de fonte (`ascii`, `hAnsi`, `eastAsia` e `cs`), sem `asciiTheme`, `hAnsiTheme`, `eastAsiaTheme` ou `cstheme`; tamanho, negrito e cor também devem ser gravados explicitamente conforme o respectivo nível, sem depender da herança do tema;
- `Heading 1`, `Heading 2` e `Heading 3` devem estar vinculados, respectivamente, aos níveis `0`, `1` e `2` do mesmo `numId`; aplicar numeração somente aos parágrafos existentes não é suficiente;
- definições do tipo `bullet`, marcadores numéricos fora de Arial ou dependentes de fontes de tema, estilos sem `numPr`, níveis ligados a listas diferentes e números digitados no texto devem reprovar a compilação.

## Estrangeirismos

- grafar em itálico palavras e expressões estrangeiras isoladas no texto em português;
- manter nomes próprios, siglas, marcas e identificadores técnicos com a grafia convencional;
- não aplicar itálico indiscriminadamente ao `ABSTRACT` nem à lista de referências, que seguem regras tipográficas próprias;
- manter `et al.` em itálico em todos os contextos.

## Sumário

- título `SUMÁRIO` em Arial 14, negrito e centralizado;
- incluir seções textuais e pós-textuais, sem elementos pré-textuais;
- entradas em Arial 12, espaçamento 1,5 e pontilhado contínuo entre o fim do título e o número da página;
- gerar o pontilhado pelo recurso automático de tabulação do Word: tab stop à direita com líder pontilhado (`w:val="right"` e `w:leader="dot"`) e um elemento `w:tab` entre título e página;
- não digitar nem calcular sequências de caracteres `.` para simular o preenchimento;
- alinhar todos os números de página na mesma margem direita, independentemente do nível da entrada;
- refletir exatamente a hierarquia e a grafia dos títulos;
- incluir `REFERÊNCIAS` sem número de seção;
- o pipeline de `README.md` deve reconstruir o sumário e conferir as páginas contra o PDF renderizado.

## Paginação

- contar as folhas a partir da folha de rosto conforme a estrutura institucional;
- não exibir o número na capa nem nos elementos pré-textuais;
- exibir a numeração a partir da primeira página da Introdução;
- manter a sequência até o final do documento.

## Referências

- título `REFERÊNCIAS` em Arial 14, negrito, centralizado e iniciado em nova página;
- entradas em Arial 12, alinhadas à esquerda e em ordem alfabética;
- espaçamento simples dentro de cada entrada e uma linha simples de separação entre entradas;
- manter cada entrada unida na mesma página sempre que couber integralmente;
- aplicar negrito uniformemente ao elemento título nas obras autônomas e ao título do periódico ou evento em artigos e trabalhos de conferência, conforme os exemplos institucionais;
- grafar `et al.` sempre em itálico, no texto, em quadros, tabelas, legendas e na lista de referências;
- não inventar nem completar metadados: título, autoria, veículo, ano, DOI e URL precisam ser verificáveis.

## Validação obrigatória

Toda alteração do DOCX deve passar por `docs/tcc/format/facens_docx.py`, renderização integral e inspeção visual de todas as páginas. A auditoria deve verificar estruturalmente a lista multinível decimal vinculada aos três estilos de título, a fonte Arial dos marcadores numéricos, a presença do tab stop automático e a ausência de pontos literais usados como líder. A auditoria automatizada não substitui a conferência visual de numeração, quebras, tabelas, sumário, rodapés e referências.
