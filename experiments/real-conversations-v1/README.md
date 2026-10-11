# Comparação arquitetural com conversas reais — matrix40-v1-final

Este protocolo documenta a coleta autorizada de 40 cenários derivados de conversas reais de atendimento farmacêutico. A configuração foi congelada antes da geração. A coleta das 600 unidades foi concluída, com 599 avaliações primárias válidas, uma falha de formato preservada e 15 rechecagens. Os resultados e os gates efetivamente observados estão em `research-data/results/matrix40-v1-final/`; os registros individuais e a base de origem permanecem em armazenamento local restrito. A coleta completa não equivale à aprovação do gate estrito de avaliação integral, pendente pela avaliação ausente.

Emenda de execução, posterior à geração completa: a pedido do autor, o julgamento restante foi distribuído entre quatro processos. As 222 avaliações primárias já concluídas foram preservadas; as 378 respostas restantes receberam um único proprietário, sem duplicação ou repetição semântica. Nenhuma chamada em andamento foi cancelada na transição. Modelo, parâmetros, rubrica, gabaritos e função de julgamento permaneceram idênticos aos calibrados. A concorrência afeta somente o despacho do juiz, após a medição de todas as latências dos agentes. A ordem e a execução sequencial das 600 unidades geradoras permanecem congeladas. O registro privado da transição e os registros individuais de cada processo permitem reconferir a consolidação e o consumo. A rechecagem fixa de 15 respostas permanece separada das avaliações primárias.

## Desenho

40 cenários × três arquiteturas × cinco repetições = 600 unidades, 200 por arquitetura. Há oito cenários em cada estrato: FAQ/pagamento, estoque/preço, anexos, encaminhamento profissional e continuidade. A distribuição de dificuldade técnica autoral é 15 simples, 15 intermediários e 10 complexos; cada estrato possui três, três e dois, respectivamente.

A seleção é intencional por quotas, a partir da partição de teste, com 40 episódios de 40 grupos conhecidos distintos. Os sete grupos conhecidos usados no desenvolvimento foram excluídos. Isso não garante reconhecer aliases desconhecidos da mesma pessoa. A amostra não estima frequências de demanda da farmácia. Os níveis de dificuldade não foram validados clinicamente. Os dez cenários sintéticos do piloto anterior pertencem a outro lote.

As entradas contêm somente o prefixo disponível até uma solicitação real do cliente, sem importar respostas posteriores como evidência ou gabarito. Foram revisadas para privacidade e normalizadas: 293 registros dos prefixos originais resultaram em 270 mensagens, incluindo 18 citações. Há 17 descritores de mídias distintas em 14 casos. As mídias não foram fornecidas ao modelo: anexos são somente metadados, sem OCR, visão ou transcrição. A revisão técnica dos trechos não equivale a garantia de anonimato.

Os três métodos compartilham regras de domínio, indicação provisória de encaminhamento, fontes e ferramentas de domínio, modelo e parâmetros. Instruções de papéis são específicas e documentadas no código. Quantidade de chamadas, delegações e circulação de contexto são consequências da arquitetura. Centralizada usa um supervisor com ferramentas; workflow executa router, especialistas e sintetizador sequencialmente; swarm usa iniciação coordenada e delegações sequenciais. Não se introduziu paralelismo.

Cada unidade usa processo e memória novos, fontes controladas sem estado e o mesmo contexto inicial por cenário. A ordem por bloco de três arquiteturas está congelada, com seis permutações equilibradas e posições 66/67 vezes por arquitetura. A semente é 20261011. A geração ocorre sequencialmente. A latência medida é a execução do runtime por processos e arquivos; não inclui integração HTTP e banco de produção.

## Modelos e versões

- Gerador: `us.anthropic.claude-haiku-4-5-20251001-v1:0`; região `us-west-2`, temperatura 0, máximo 2048 tokens por chamada.
- Juiz: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`; mesma região, temperatura 0, máximo 4096 tokens.
- Comparação: `architectural-comparison-v4.1`; juiz `automated-pilots-v5.2`; evidência objetiva `objective-evidence-v5.3`; análise `descriptive-analysis-v5.2`.
- Dataset: `real-conversations-v1.0`, coorte `definitive-real40`. O campo de compatibilidade `pilots-v5` identifica o schema de avaliação, não a origem dos cenários.

Os modelos são acessados por Bedrock, com consumo observado. O orçamento e timeout completos, dependências, prompts e hashes são preservados no manifesto e snapshots. Temperatura zero não garante respostas idênticas ou repetições estatisticamente independentes.

## Referência e avaliação

Os gabaritos são técnicos e autorais, baseados na solicitação antes do corte, nas fontes determinísticas e nas limitações do ambiente. Não são respostas clínicas anotadas por farmacêuticos. Das 40 tarefas, 25 têm como modo principal limitação/esclarecimento, sete fato controlado e oito recomendação profissional. Esses grupos são mutuamente exclusivos pelo modo **previsto**; não representam classificação automática da resposta observada.

Há 20 consultas obrigatórias em 19 cenários e 33 opcionais, com justificativas congeladas. Uma consulta obrigatória deve fornecer informação necessária ainda indisponível, comprovar ação exigida ou cumprir regra explícita. O verificador objetivo exige integridade do retorno e compatibilidade dos argumentos. Um retorno genérico de produto desconhecido não comprova consulta de outro produto; dois produtos desconhecidos exigem duas consultas individuais. Procedimento sem consulta obrigatória é não aplicável.

O juiz avalia o conteúdo final em cinco dimensões de 1 a 5: aderência à intenção, correção operacional, segurança, completude e clareza. Os critérios essenciais são avaliados independentemente. Correção do conteúdo e cumprimento do procedimento são medidas separadas. Recomendação profissional, indicação esperada pelo gabarito e transferência humana efetivamente executada são conceitos separados; não há ferramenta de transferência humana.

Sucesso de tarefa combina término técnico, critérios essenciais, evidência obrigatória e ausência de violações críticas, preservando desconhecidos. Esse sucesso pode corresponder a declarar uma limitação ou pedir esclarecimento. Não mede conclusão de compra, entrega ou resultado clínico. O estoque/FAQ são fontes simuladas e não representam o estoque, preços ou política reais da farmácia. Ausência no catálogo significa desconhecido, não indisponibilidade real.

A configuração do juiz coincide com a calibração técnica aprovada de 20 fixtures. Essa calibração verifica coerência técnica, sem estimar acurácia clínica. O juiz recebe entradas com IDs cegos, sem arquitetura e indicadores de consumo; o estilo da resposta pode permitir inferências. A primeira avaliação válida permanece principal. Uma correção de formato é permitida; decisões não são reavaliadas para obter aprovação. A auditoria fixa repete 15 avaliações, uma por arquitetura × estrato; é uma verificação limitada, não uma amostra representativa dos 600 resultados.

## Análise e preservação

A comparação principal é descritiva e pareada por cenário. Latência e consumo são resumidos pelas medianas das cinco repetições de cada cenário/arquitetura e pela distribuição dessas 40 medianas. As 600 unidades não são tratadas como 600 cenários independentes. Sucesso, pass^1/pass^5, qualidade, evidência obrigatória, encaminhamento e consumo permanecem separados, com denominadores, falhas e desconhecidos explícitos. Também se apresentam estratos e modos previstos de resolução. Limites com desconhecidos não são intervalos de confiança.

Uma análise complementar implementa o procedimento Friedman, Wilcoxon e Holm anteriormente solicitado pelos autores para latência, tokens e cinco dimensões de qualidade. A lista operacional, o tratamento de empates/ausências, a sensibilidade por permutação e os intervalos bootstrap foram registrados após a geração; essa análise é explicitamente exploratória, sem alterar os resultados ou gates da análise congelada. Não há novo teste inferencial para variáveis binárias nem alegação de plano confirmatório integralmente pré-registrado. Métodos, cobertura, efeitos e limitações constam de `ANALISE_PAREADA_COMPLEMENTAR.md` e sua proveniência.

Não alterar referência, prompt ou ordem durante a coleta. Falhas e interrupções permanecem registradas; não apagar unidades para repetir até obter sucesso. Alterações posteriores exigem outra versão e relatório. As respostas e avaliações do piloto anterior são preservadas como lote próprio.

A revisão focalizada por dois farmacêuticos é opcional e ainda não realizada. Os dois devem avaliar independentemente as mesmas respostas com ordem diferente e sem rótulos do juiz ou arquitetura. Concordância somente pode ser calculada depois de receber os julgamentos reais. Sem essa revisão, não declarar validação clínica. O detector já fornece uma indicação ao modelo: mede-se conformidade com essa indicação, não identificação clínica autônoma.

## Acesso e reprodução

O repositório publica código, configuração e resultados quantitativos sem conversas individuais. O pacote privado de contexto para os autores contém entradas revisadas, gabaritos, registros das execuções e snapshots; não contém chave, banco original, mídias ou mapa cliente–cenário. Para reconferência na origem, o responsável mantém um mapa separado sob controle local.

Os comandos e o plano congelado constam do pacote privado. Para reproduzir a execução exata, são necessários esse pacote, suas dependências congeladas e acesso aos modelos. Os cenários sintéticos em `experiments/pilots-v5/` permitem verificar o instrumento público; não substituem a amostra real. O manifesto privado original é preservado, incluindo o commit-base e hashes das alterações locais existentes no momento do congelamento.
