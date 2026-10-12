# Capturas do MAB para o TCC

Acervo recebido dos autores em 12 de outubro de 2026 e revisado para publicação. As telas de resultados apresentam registros existentes em uma visualização posterior, somente em leitura. O Swagger documenta os contratos dos serviços locais. Nenhuma nova execução, avaliação ou rechecagem foi realizada para preparar este acervo.

## Organização

| Diretório | Conteúdo | Uso editorial |
|---|---|---|
| `01-painel-e-indice` | Totais da coleta, índice filtrável e consumo | Visão geral e consulta dos registros |
| `02-comparacao` | Comparação de respostas geradas no mesmo cenário | Exemplo de entrada comum e resultados distintos |
| `03-trajetorias` | Supervisor, especialistas, sintetizador e delegações | Inspeção da ordem registrada dos agentes |
| `04-falhas` | Conteúdo não atendido e consulta obrigatória ausente | Exemplificação da classificação das falhas |
| `05-contexto-e-anexos` | Registro da seleção de descritores | Painel técnico publicado em `publicacao`, com histórico omitido |
| `06-api` | Rotas e modelos da API transacional no Swagger | Contratos de execução, comparação, eventos e projeção |
| `07-runtime` | Despacho e aceitação do serviço de agentes | Contratos `RuntimeDispatchRequest` e `RuntimeDispatchResponse` |
| `08-arquitetura` | Diagrama SVG/PNG, fonte DOT e fontes de código | Acervo de apoio; o diagrama conciso do documento foi preservado |
| `publicacao` | Nove figuras derivadas para o documento | Recortes com pixels e valores preservados; composição de painéis quando indicada |
| `contratos` | OpenAPI e inventários da API e do runtime | Conferência dos métodos, caminhos e campos |

`inventario.json` classifica os 28 arquivos visuais recebidos, incluindo as duas versões do diagrama. Foram arquivadas 22 capturas de tela e as versões PNG/SVG do diagrama. Quatro imagens integrais receberam classificação restrita porque incluem mensagens históricas ou contexto individual de medicamento e orçamento. Seus arquivos originais não foram publicados; os descritores e requisitos técnicos pertinentes foram recortados para as figuras de publicação.

Os dados `apresentacao.json`, o exemplo GET com detalhes, as transcrições e os anexos originais permanecem fora do repositório público, conforme `docs/tcc/data-governance.md`. Os identificadores presentes nas capturas são técnicos e não acompanhados de uma tabela de reversão para participantes.

## Evidência e limites

O lote contém 40 cenários, três arquiteturas e cinco repetições: 600 unidades, 356 sucessos da tarefa, 244 falhas e 599 julgamentos principais válidos. As 600 linhas do índice recebido foram comparadas, campo a campo, ao arquivo original `aggregated-evaluations.jsonl`. Os 58 arquivos abrangidos pelo inventário SHA-256 do pacote tiveram tamanho e hash conferidos.

Os serviços não participaram da medição por HTTP ou PostgreSQL. O experimento chamou diretamente o núcleo dos agentes por processos e gravou registros em arquivos. Para as capturas, o Coder preparou uma rota `/research-captures` no frontend e um índice SQLite separado em leitura. A indisponibilidade do banco transacional impediu comprovar consultas operacionais ou SSE sobre as 600 unidades nesse banco. As capturas do Swagger descrevem contratos; exemplos automáticos não são respostas do lote.

O código examinado nas capturas corresponde ao commit `3fa15c4140fc701edf1967f1217576cebdd106cf`, com uma rota de apresentação acrescentada localmente pelo Coder. O manifesto experimental registra `e6a638f85502566a9d93e436359e98a292861f77` e SHA-256 `921b54f9310e3281c519e5b61100304aa3a4755a27daf0238a96c3910f4cf208`. A comparação do instrumento por conteúdo realizada pelo Coder está descrita em `arquitetura_fontes.md` e no relatório recebido. `validacao.json` separa as verificações desta revisão editorial das características registradas na origem.

## Seleção para o documento

| Figura de publicação | Conteúdo | Seção |
|---|---|---|
| `01-painel-geral` | Totais da coleta, em dois recortes da mesma tela | 5.3 Recursos de acompanhamento |
| `02-comparacao-cenario` | Valores individuais de R-stock-03, repetição 0, nas três arquiteturas | 5.3 Recursos de acompanhamento |
| `03-percursos-agentes` | Invocações do mesmo cenário, com identificação dos três painéis | 6.2 Implementação das arquiteturas |
| `04-descritores-anexos` | Aliases, MIME, tamanho e limites de leitura, sem histórico | 6.3 Ferramentas de domínio |
| `05-swagger-rotas-api` | Execução, comparação, SSE e integração | 6.4 API e registro dos eventos |
| `06-swagger-modelos-api` | Modelos de leitura e comparação | 6.4 API e registro dos eventos |
| `07-swagger-modelos-runtime` | Modelos de entrada e aceitação | 6.4 API e registro dos eventos |
| `08-falha-faq` | Omissão do horário controlado e da consulta E1 | 7.9 Classificação e análise das falhas |
| `09-falha-recomendacao` | Requisitos C3/C4 e consulta E1 pendentes, sem contexto individual | 7.9 Classificação e análise das falhas |

Cada recorte possui coordenadas, hash de origem e transformação em `inventario.json`. As imagens de publicação não foram redimensionadas internamente. Os arquivos SVG de publicação incorporam o PNG: são envelopes de compatibilidade para o pipeline do Word, não redesenhos vetoriais da interface. O original integral publicável continua no diretório de sua categoria.

No documento, as figuras usam legenda automática `SEQ Figura`, imagem inline centralizada, nota de fonte e espaço de 6 pt após a legenda. A renumeração, o sumário e a lista de figuras seguem o pipeline Facens em duas passagens. A versão atualizada do documento foi entregue separadamente aos autores.
