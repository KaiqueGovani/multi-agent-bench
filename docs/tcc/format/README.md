# Formatação automática do DOCX — Facens

Este diretório contém a etapa obrigatória de pós-processamento do documento Word do TCC. Ela corrige e valida a estrutura editorial sem alterar o conteúdo acadêmico.

## Pipeline obrigatório

Após qualquer sincronização do manuscrito com `/TCC/TCC_MAB_Facens_Ralph_10x.docx`, execute o fluxo em duas passagens:

```bash
python docs/tcc/format/facens_docx.py prepare \
  /TCC/TCC_MAB_Facens_Ralph_10x.docx \
  /tmp/tcc-facens-pass1.docx

python /root/.codex/skills/slides/container_tools/render_docx.py \
  /tmp/tcc-facens-pass1.docx \
  --output_dir /tmp/tcc-facens-pass1-render \
  --emit_pdf

python docs/tcc/format/facens_docx.py finalize-toc \
  /tmp/tcc-facens-pass1.docx \
  /tmp/tcc-facens-pass1-render/tcc-facens-pass1.pdf \
  /TCC/TCC_MAB_Facens_Ralph_10x.docx

python /root/.codex/skills/slides/container_tools/render_docx.py \
  /TCC/TCC_MAB_Facens_Ralph_10x.docx \
  --output_dir /tmp/tcc-facens-final-render \
  --emit_pdf

python docs/tcc/format/facens_docx.py audit \
  /TCC/TCC_MAB_Facens_Ralph_10x.docx \
  --pdf /tmp/tcc-facens-final-render/TCC_MAB_Facens_Ralph_10x.pdf
```

O caminho de `render_docx.py` pode variar no ambiente. Quando isso ocorrer, use o renderizador indicado pela skill de documentos, mantendo as duas passagens.

## O que o formatador garante

- página A4 e margens Facens;
- estilos hierárquicos de capítulos e subseções;
- nível 1 em Arial 14, negrito e caixa alta; nível 2 em Arial 12, negrito e caixa alta; níveis 3 ou superiores em Arial 12 e caixa alta;
- títulos em preto absoluto, com remoção de `themeColor`, `themeTint` e `themeShade` do OOXML;
- numeração multinível única e reinício coerente entre capítulos;
- capítulos de primeiro nível iniciando em nova página;
- uma linha e meia antes e depois dos títulos, sem intervalo duplicado entre títulos consecutivos;
- corpo em Arial 12, justificado, espaçamento 1,5 e recuo de primeira linha;
- palavras e expressões estrangeiras isoladas em itálico, com preservação das exceções bibliográficas;
- sumário estático reproduzível, com links internos, caracteres `.` reais calculados até uma coluna única de páginas e páginas conferidas no PDF;
- referências em ordem alfabética, alinhadas à esquerda, espaço simples, uma linha de separação, entrada não fragmentada quando couber e destaque bibliográfico uniforme em negrito;
- `et al.` sempre em itálico, inclusive em tabelas e referências;
- paginação visível a partir da Introdução, sem exibir número na capa e nos elementos pré-textuais;
- preservação dos placeholders dos capítulos protegidos pelos evidence gates.

## Por que o sumário é estático

Atualizadores de campos do Word não estão disponíveis de forma confiável em execuções sem interface gráfica. O formatador gera um sumário estático com hiperlinks internos e calcula as páginas a partir do PDF renderizado. Assim, o arquivo entregue já abre com o sumário correto, sem depender de `F9` ou de “Atualizar campos”.

O DOCX só está pronto para commit quando `audit` encerrar com `OK` e todas as páginas renderizadas tiverem sido inspecionadas visualmente.
