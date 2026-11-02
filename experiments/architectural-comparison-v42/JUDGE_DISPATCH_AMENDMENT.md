# Emenda de despacho do julgador

Em 02/11/2026, durante a geração sequencial e antes de qualquer julgamento do novo lote principal, o autor solicitou maior paralelismo para reduzir o tempo de execução. Após explicitar a diferença entre alterar a geração e paralelizar a avaliação, escolheu **paralelizar somente o julgamento e manter a geração atual**.

A geração das 600 unidades mantém o transporte, a ordem, a configuração e as fronteiras de latência congeladas. Nenhuma tentativa é substituída e nenhum resultado antigo é reutilizado. Somente a avaliação principal e a rechecagem das 15 unidades previamente selecionadas usam quatro processos independentes.

Cada resposta tem um proprietário durável exclusivo. O despachante impede inferência duplicada, preserva tentativas já iniciadas e consolida os registros pelos identificadores únicos das requisições físicas. Os arquivos por proprietário e o registro consolidado representam as mesmas chamadas; somá-los duplicaria consumo. Interrupções e falhas permanecem identificadas, sem comprar um julgamento alternativo.

Modelo Sonnet, região us-west-2, temperatura zero, máximo de 4.096 tokens, referências, rubrica, schema, reparo exclusivamente de formato e cegamento permanecem iguais. O SHA-256 do sistema do julgador continua `ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36`. A atribuição das respostas aos processos não depende de notas ou de sucesso. Nenhum processo recebe arquitetura, custo ou latência no contexto do julgador.

A emenda integral e a identificação do despachante ficam no pacote restrito, em `main-600-01/judge-dispatch-amendment.json`. Sua implementação e consolidação são verificadas com respostas controladas antes de iniciar a inferência principal. O tempo de avaliação é separado das latências sequenciais da geração; a nova concorrência não autoriza apresentar essas latências do núcleo como desempenho da API em produção.

O despachante reproduzível está em `scripts/parallel_judge.py`. Seis testes controlados em `tests/test_parallel_judge.py` passaram com `-W error`, incluindo quatro subprocessos retomando registros sintéticos já concluídos sem novas chamadas. Uma revisão independente verificou propriedade exclusiva, retomada sem repetição de chamadas iniciadas, preservação do prefixo original, cegamento, parâmetros, seleção fixa das rechecagens e consolidação das requisições físicas. Os 33 hashes do código congelado da geração permaneceram iguais.
