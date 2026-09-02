# Acervo de figuras do TCC

Este diretório reúne candidatos visuais pesquisados para o TCC e os registros necessários para decidir, posteriormente, quais figuras entrarão no manuscrito. A presença de um arquivo em `candidates/` **não significa aprovação para publicação**.

## Estrutura

- `inventory.csv`: inventário rastreável, com origem, licença, transformação, seção possível e decisão editorial.
- `research-2026-08-24.md`: auditoria inicial das referências já citadas e mapa de lacunas visuais.
- `research-2026-08-24-02.md`: busca aprofundada em documentação oficial, papers e artigos.
- `research-2026-08-31.md`: auditoria visual do DOCX atual, mapa priorizado de pontos de inserção e revisão das figuras presentes nas 16 referências citadas.
- `candidates/`: cópias ou recortes de figuras cuja reutilização foi autorizada pela licença da fonte e cuja proveniência foi registrada.
- `editable/`: fontes vetoriais editáveis de adaptações e diagramas candidatos.
- `original/`: reservado para diagramas autorais do TCC, preferencialmente em formato vetorial e com uma fonte editável.
- `original/insertion-map-2026-09-02/`: 14 diagramas autorais em SVG derivados do mapa de inserções; candidatos validados visualmente e ainda não aprovados para o DOCX.
- `approved/`: reservado para as versões finais aprovadas e prontas para o DOCX.

As figuras metodológicas aprovadas ficam em `approved/methodology/`. Cada figura mantém o SVG como fonte principal e um PNG de alta resolução como *fallback* de compatibilidade e visualização.

## Regras do acervo

1. Não salvar no repositório uma figura com direitos de reutilização incertos. Nesse caso, registrar apenas a referência e a recomendação de criar um diagrama autoral.
2. Cada arquivo precisa ter uma linha em `inventory.csv`, URL da fonte primária, licença, modificação realizada e atribuição sugerida.
3. Recorte, tradução, redesenho ou simplificação devem ser identificados como adaptação. A licença da fonte precisa permitir a transformação.
4. Antes da aprovação, verificar legibilidade em tamanho de página, contraste em escala de cinza, coerência com o texto, necessidade de tradução e ausência de dados pessoais.
5. Figuras do protótipo devem ser produzidas somente quando a implementação correspondente estiver estabilizada. Código pode ser consultado em modo leitura; o trabalho documental não altera o protótipo.
6. Gráficos de resultados não podem ser preparados nem inseridos enquanto os *evidence gates* de resultados, discussão e conclusão permanecerem fechados.
7. A lista de figuras deverá ser gerada automaticamente a partir das legendas do Word. Não manter lista manual nem números de página digitados.
8. Imagens de páginas corporativas sem licença de reutilização explícita servem apenas como referência conceitual para um redesenho próprio; captura de tela não substitui autorização.
9. Figuras inseridas no DOCX devem ser `inline`, centralizadas, acompanhadas de legenda numerada automaticamente e nota de fonte. O DOCX deve embutir o SVG e conservar o PNG como *fallback* para renderizadores que não suportem SVG.
10. O pipeline Facens deve reconstruir a lista de figuras a partir das legendas e calcular as páginas na segunda passagem, com tabulação à direita e líder pontilhado automático; números e pontos digitados manualmente são proibidos.

## Fluxo de promoção

`candidate` → revisão conceitual e jurídica → adaptação ou redesenho, se necessário → validação visual → `approved` → inserção no manuscrito e no DOCX → atualização automática da lista de figuras.

Ao inserir uma figura, a legenda deve explicar o que ela mostra e a nota de fonte deve distinguir claramente entre reprodução, adaptação e elaboração própria.

O mapa de 31 de agosto recomenda aprovar primeiro um conjunto enxuto de seis a oito figuras, concentrado na anatomia de agentes, comparação das três arquiteturas, síntese dos trabalhos correlatos e arquitetura lógica do MAB. Figuras dos capítulos 7 a 9 permanecem adiadas enquanto os respectivos *evidence gates* estiverem fechados.
