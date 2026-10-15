# Parecer da orientadora de 14 de outubro de 2026

## Origem e escopo

- Revisora: Ma. Talita dos Reis Lopes Berbel.
- Fonte: `TCC_MAB_Prompts_Julgador_2026-10-12_Revisado_Talita.docx`, fornecido pelo autor.
- Marcas extraídas: 12 comentários e 14 parágrafos destacados.
- Pedido: corrigir os pontos assinalados, estender os aprendizados ao documento, atualizar o Report 6 e registrar os ajustes pertinentes no GitHub.
- Esta é uma revisão editorial solicitada pelo autor, não uma nova execução do experimento. As 600 execuções e os julgamentos originais foram preservados.

## Tratamento dos comentários

| Comentário | Ponto observado | Correção |
|---|---|---|
| 72 e 73 | Abertura dos resultados começava diretamente com percentuais | Inserido contexto sobre a comparação e seus indicadores antes dos números. |
| 74 | Alcance da ausência de revisão farmacêutica | Esclarecida a diferença entre processamento medido, conformidade técnica com o gabarito e avaliação profissional das respostas. |
| 77 | Alternância de nomes para o workflow | Padronizada a nomenclatura depois da apresentação dos nomes completos. |
| 82 | Referência de comparação pouco clara | Definidas a comparação do mesmo cenário, a centralizada como referência, a diferença absoluta e a razão calculada antes da agregação. |
| 85 | Esclarecimento confundido com categoria de demanda | Definido o tipo de resolução, incluindo o agrupamento dos tipos combinados do gabarito; preservadas as cinco categorias de demanda. |
| 87 | Medianas de qualidade apresentadas sem contexto local | Retomadas as cinco dimensões, a escala de 1 a 5 e a mediana das notas válidas. |
| 94 e 95 | Explicação metodológica estava na fonte da tabela | Explicações transferidas para o texto, junto aos valores. A regra foi aplicada a outras fontes com ressalvas analíticas. |
| 101 | Exemplos pareciam uma enumeração incompleta do catálogo | Declarado o caráter ilustrativo dos casos e das telas, com limites da leitura qualitativa. |
| 103 | Resultados terminavam sem interpretação de conjunto | Integrada a discussão como seção de fechamento dos resultados, com síntese e limites. |
| 110 | Subdivisões das considerações finais | Removidos os subtítulos; conclusão e possibilidades de continuidade passaram a formar texto corrido. |

Com a integração da discussão ao capítulo 7, as considerações finais passaram a ser o capítulo 8. Essa renumeração é consequência da estrutura final e é gerada pela lista multinível do Word.

## Aprendizados reaplicados

1. Todo título deve ser seguido por texto antes do próximo título, independentemente dos níveis. Espaços vazios ou ilustrações não substituem esse texto.
2. O parágrafo de abertura situa o objetivo da análise; percentuais e contagens são apresentados depois dessa contextualização.
3. Termos estatísticos precisam de escala, unidade, operação e referência de comparação. A mediana das razões de cada cenário não é a razão entre medianas gerais.
4. Categoria de demanda, dificuldade e tipo de resolução são atributos diferentes. Os sete tipos de resolução registrados no gabarito foram apresentados em quatro grupos analíticos, explicitando as combinações.
5. Nomes de arquiteturas devem permanecer consistentes. Códigos só ajudam o leitor quando seus componentes e seu âmbito local estão definidos.
6. Fontes de ilustrações devem identificar proveniência; o texto apresenta cálculos, critérios, denominadores e ressalvas. A interpretação deve continuar depois da ilustração.
7. Casos particulares ilustram as contagens e não demonstram uma causa geral de falha. Uma inspeção posterior não deve ser descrita como experimento de ablação.
8. A discussão deve relacionar resultados, literatura e limites. A retirada de subtítulos das considerações finais não elimina os trabalhos futuros, inclusive a proposta centrada em problemas do atendimento farmacêutico.
9. A orientação mais recente exige títulos de figuras em Arial 12. A revisão preserva fonte em Arial 10, espaço após legendas, ordem legenda–imagem–fonte, numeração automática, itálico e líderes de tabulação.
10. O sumário deve distinguir um título verdadeiro de uma palavra repetida no corpo, inclusive nos prompts dos apêndices. A bibliografia termina antes desses apêndices.

## Preservação e publicação

O commit contém regras, utilitário de formatação e este registro. Os documentos revistos são entregues ao autor separadamente. Não são versionados o DOCX comentado, o conteúdo de conversas, entradas dos cenários ou trajetórias restritas. Os controles históricos de evidência da rotina autônoma permanecem inalterados; esta revisão não deve ser confundida com autorização para novas coletas ou alteração de julgamentos.

## Validação

Os dois documentos passaram pelo pipeline de duas passagens e pela auditoria Facens. O TCC final tem 105 páginas, 30 figuras, 25 tabelas numéricas, seis quadros e 45 referências. O Report 6 tem 34 páginas, 13 figuras, 15 tabelas numéricas e 15 referências. Todas as referências finais têm citação, e todas as citações têm entrada correspondente em cada documento.

A conferência estrutural não encontrou títulos consecutivos sem texto, ilustrações sem menção anterior, comentários residuais ou destaques de revisão. As páginas renderizadas foram inspecionadas; a passagem final também conferiu a numeração de todas as páginas, a integridade dos arquivos de imagem, o sumário e os blocos dos apêndices. As 31 tabelas e os 30 pares SVG/PNG do TCC de origem foram preservados, assim como o texto literal dos prompts e exemplos de código. O registro completo da execução está em `../state/runs/2026-10-14-advisor-review.md`.
