# Revisão crítica do Capítulo 2 e dos 14 SVGs

Data: 7 de setembro de 2026. Origem: solicitação direta dos autores para revisão integral do capítulo e seleção editorial das figuras. Base: `42b0ef1479a8979ffd302673346df026e8e5f2b5`. Branch: `agent/tcc-ralph-setup`.

## Diagnóstico e mudanças aplicadas

O capítulo anterior tinha uma sequência temática adequada, mas distribuía explicações breves em muitas subseções. A introdução ao atendimento ocupava espaço desproporcional ao objeto comparativo; algumas definições eram genéricas e a comparação final repetia descrições sem delimitar o que, efetivamente, varia no experimento.

1. **2.1 e 2.2:** reunidas as seis subseções curtas nos dois tópicos principais. Conservados contexto operacional, limites da automação e distinção entre interface conversacional e processamento. Retiradas enumerações e promessas genéricas de benefícios.
2. **2.3:** desenvolvidos token, geração autorregressiva, atenção, contexto versus treinamento, agente e ferramenta. Quatro fontes acadêmicas acrescentadas para sustentar diretamente esses conceitos. O ciclo de ferramentas distingue solicitação do modelo de execução pela aplicação.
3. **2.4:** preservada a profundidade sobre interação; separadas topologia, autoridade, comunicação e coordenação. A observabilidade foi relacionada ao percurso técnico, sem equivalê-la à qualidade semântica. Riscos de interação foram apresentados com o nível de evidência da fonte.
4. **2.5:** reescritas as três formas de coordenação com definição, consequência de projeto e limitação. Retirada a repetição de exemplos de atendimento. O texto final explicita que o MAB compara configurações completas, com diferenças no número e nos papéis dos agentes, e não apenas desenhos de conexões.
5. **Linguagem:** reduzidas frases de efeito, qualificadores e abstrações; usados exemplos concretos somente quando explicam uma distinção. Mantidos termos técnicos necessários, acompanhados de explicação em português.
6. **Coerência com 4.2:** corrigida a afirmação de que não haveria agente único; esclarecido que não será adicionada uma quarta condição de referência. A condição centralizada existente utiliza um agente com ferramentas. Essa correção documental não altera o desenho de três condições.
7. **Limites:** nenhuma arquitetura é declarada superior. A farmácia permanece estudo de caso. Não foram antecipados resultados nem alteradas decisões pendentes de governança.

O registro bibliográfico preserva as referências retiradas deste capítulo quando ainda citadas em outro trecho. Metadados e aplicação de R064–R067 estão em `docs/tcc/references/verification-2026-09-07.md`.

## Revisão dos diagramas

Todos os 14 originais foram renderizados e observados antes do redesenho; as versões corrigidas foram renderizadas novamente e inspecionadas individualmente. Correções comuns: ancoragem das setas, espaçamento entre caixas, ausência de texto sobre conectores, alinhamento de ramos, contraste e redução de rótulos sem função explicativa. O conteúdo segue em SVG editável; PNGs de 1800 pixels servem como compatibilidade.

A autorização dos autores permite selecionar e inserir as figuras após revisão. Foram escolhidas cinco, com funções distintas. As outras nove foram corrigidas e preservadas, mas não inseridas para evitar repetição ou representar protocolo ainda não congelado.

| ID / arquivo | Correção principal | Decisão |
|---|---|---|
| C019 / 01 | Controle e transições separados; esquema conceitual não confundido com população de agentes do MAB. | Inserida em 2.5.4. |
| C020 / 02 | Retorno da ferramenta fecha o ciclo; a aplicação executa a chamada. | Inserida em 2.3.2. |
| C021 / 03 | Relações de comunicação e acesso desenhadas de forma explícita. | Acervo; sobrepõe ciclo e topologias. |
| C022 / 04 | Conexões completas; removida associação imprecisa de topologias a estudos específicos. | Inserida em 2.4.2. |
| C023 / 05 | Excluída matriz de cobertura sem critérios verificáveis; novo quadro de perguntas de leitura. | Acervo; não substitui matriz do Capítulo 3. |
| C024 / 06 | Banco e anexos ligados à API; arquiteturas como alternativas do serviço de execução. | Inserida em 5.2. |
| C025 / 07 | Sequência com quatro participantes e retornos identificáveis. | Acervo; 5.4 já explica o fluxo. |
| C026 / 08 | Número de agentes e distribuição de funções reconhecidos como diferenças. | Inserida em 6.3. |
| C027 / 09 | Separadas consulta operacional e necessidade de avaliação profissional. | Acervo; contexto já suficiente em 2.1. |
| C028 / 10 | Removida escada que sugeria evolução obrigatória de chatbot a multiagentes. | Acervo; texto já diferencia os componentes. |
| C029 / 11 | Quatro dimensões ligadas ao objetivo; rótulos ajustados às caixas. | Acervo; evitar duplicar avaliação híbrida. |
| C030 / 12 | Ramos sim/não completos; mantida a natureza de plano estatístico. | Acervo; aguardar revisão do protocolo. |
| C031 / 13 | Proveniência separada de resultados e avaliação. | Acervo; congelamento ainda pendente. |
| C032 / 14 | Camadas simplificadas, tecnologias separadas dos registros. | Acervo; sobrepõe serviços e 6.1. |

IDs completos usam o prefixo `IMG-`. Nomes históricos dos arquivos foram preservados, inclusive 05 e 10, cujo conteúdo foi reformulado. Os hashes de SVG/PNG, dimensões e decisões estão em `docs/tcc/figures/original/insertion-map-2026-09-02/validation-2026-09-07.json`. O ZIP do acervo foi atualizado.

## Validação e pendências

As cinco inserções usam SVG com PNG de compatibilidade, texto alternativo, legenda por campo SEQ e fonte. As quatro figuras metodológicas já presentes foram preservadas; a numeração das nove figuras e a lista foram recalculadas. O DOCX passa pelo pipeline Facens em duas passagens, auditoria estrutural e inspeção visual, registradas no relatório desta execução.

OQ-004 e OQ-005 foram consultadas no GitHub: abertas, sem comentários novos. Não houve resposta humana a integrar nem nova questão a abrir. Coleta permanece NO-GO; os gates de resultados, discussão e conclusão continuam fechados. Nenhum arquivo do protótipo foi alterado.
