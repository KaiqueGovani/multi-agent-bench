# Índice das comparações

Os lotes são separados e não devem ser agrupados.

- [`architectural-comparison-v44/`](architectural-comparison-v44/RELATORIO.md): último experimento, com 600 tentativas nos 40 cenários originais, supervisor corrigido e comparadores v4.2. Use `make research-results` e abra [a visualização v4.4](http://127.0.0.1:3000/research/comparison-v44) para consultar os dados versionados.
- [`architectural-comparison-v43/`](architectural-comparison-v43/RELATORIO.md): experimento separado com 360 tentativas em casos sintéticos e condição descentralizada com autoridade final no especialista.
- `matrix40-v1-final/`: comparação histórica, protocolo v4.1. A condição centralizada deste lote executou **um único agente com ferramentas de domínio**; seus números não representam o supervisor multiagente corrigido. Os arquivos e valores históricos são preservados.
- `agents-as-tools-v42/`: nova comparação do supervisor com especialistas como ferramentas, workflow e swarm. Seus resultados só são publicados após a coleta e avaliação completas das 600 unidades novas; não reutilizam respostas históricas.

O protocolo, as definições e a validação técnica da correção estão em `experiments/architectural-comparison-v42/`, na raiz do repositório. As mensagens, gabaritos, trajetórias e avaliações integrais ficam no pacote restrito dos autores.

Uma comparação histórica entre os lotes é descritiva e não identifica efeito causal da correção. Nenhum dos lotes constitui validação clínica ou revisão farmacêutica.
