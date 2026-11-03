# Consulta local da coleta congelada

A rota `/research` reúne links para as comparações publicadas. Com a consulta privada habilitada no servidor local, a mesma página também mostra o lote histórico `matrix40-v1-final`. `/research-captures` redireciona para ela.

O servidor lê os 600 registros e os detalhes uma vez, mantendo uma cópia de apresentação em RAM. A consulta usa apenas `GET /api/research` e `GET /api/research?run=<run_id>`, na mesma origem. Não importa dados em PostgreSQL/SQLite, não executa agentes, não chama o juiz e não precisa de credencial Bedrock. Reiniciar o servidor descarta a memória. Nenhum arquivo da coleta é escrito.

## Abrir

Com Node 22.13 ou mais recente e os arquivos privados da coleta no ambiente local, habilite a consulta explicitamente e vincule o servidor ao endereço de loopback:

```sh
cd apps/web
MAB_ENABLE_PRIVATE_REPLAY=1 NEXT_PUBLIC_API_KEY='' npm run dev -- --hostname 127.0.0.1 --port 3100
```

Abra `http://127.0.0.1:3100/research` diretamente, em um processo dedicado ao acesso local. O vínculo TCP em loopback é parte da barreira de acesso. Evite encaminhar esse servidor por proxy, túnel ou publicação de porta. O servidor verifica o endereço e a porta do listener antes de consultar os arquivos. Requisições externas e o modo padrão recebem `404` genérico. A configuração vale apenas para o replay privado, e as comparações publicadas têm rotas próprias.

O caminho padrão é `var/reports/real-conversations-v1/matrix40-v1-final`, relativo à raiz do repositório. `MAB_REPLAY_SOURCE` pode fornecer outro caminho absoluto para o mesmo lote. O manifesto deve corresponder ao SHA-256 congelado.

Para usar o build de produção local, execute `npm run build` e depois `MAB_ENABLE_PRIVATE_REPLAY=1 NEXT_PUBLIC_API_KEY='' npm run start -- --hostname 127.0.0.1 --port 3100`. Use diretórios de build separados para instâncias simultâneas.

## Inspeção

- Visão geral: sucesso da tarefa separado de conclusão técnica, juiz válido, medianas por cenário.
- Execuções: filtros combinados, ordenação, paginação completa, CSV de métricas e inspeção individual.
- Detalhes: histórico anterior, descritores de anexos, resposta, gabarito, avaliações, procedimento, encaminhamento, agentes, ferramentas, eventos e comparação pareada.
- Cenários: as 40 linhas, com sucessos nas cinco repetições de cada arquitetura.
- Qualidade e consumo: distribuições das cinco notas, consumo separado entre geração/juiz/rechecagem e sucesso por modo de resolução.

Um link com `?run=<run_id>` abre diretamente a execução; recarregar e voltar no navegador preservam esse destino. As repetições são as originais, de 0 a 4. O julgamento inválido permanece ausente; as rechecagens não substituem a avaliação principal. Contatos são removidos da cópia exibida. Não se publica a base privada nem binários dos anexos.

## Validar

```sh
npm run typecheck
npm run test:e2e -- research-replay-guard.spec.ts --workers=1
MAB_ENABLE_PRIVATE_REPLAY=1 npm run test:e2e -- research-replay-guard.spec.ts research-replay.spec.ts --workers=1
```

Use um servidor novo para cada modo. A configuração Playwright pode reutilizar um processo já iniciado, com o ambiente desse processo. Os testes `research-replay.spec.ts` conferem os 600 detalhes, as métricas, os hashes e as entradas pareadas da coleta local quando o opt-in e os arquivos estão presentes. Os testes da guarda verificam o modo padrão e a rejeição de requisições externas.

`ui-audit.spec.ts` registra capturas e vídeos antes/depois em `research-data/local/auditoria-ui-20261012`, que permanece fora do Git. `MAB_AUDIT_PHASE=antes` serve somente para reproduzir os testes contra a versão anterior às correções; não corresponde ao comportamento esperado da versão atual.
