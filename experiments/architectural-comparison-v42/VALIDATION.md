# Liberação técnica da coleta v4.2

Validação realizada em 02/11/2026, antes do lote principal. Implementação congelada no commit `10ef1f1` (branch `codex/agents-as-tools-v42`); o manifesto de cada fase registra o hash completo efetivamente utilizado.

| Verificação | Resultado |
|---|---|
| Runtime: agentes reais do SDK com provedor controlado, hierarquia, limites e isolamento | 193 testes aprovados com `-W error` |
| API, metadados, eventos e verificação de fontes | 52 testes aprovados |
| Interface: grafo observado e regressões pertinentes | 13 testes Chromium aprovados; duas verificações direcionadas após o ajuste final |
| Análise: pareamento, Holm, tokens, custos desconhecidos e classes de falha | 14 testes aprovados |
| TypeScript | sem erros |
| API real: FAQ, estoque, anexos e múltiplas fontes | quatro casos, primeiras execuções preservadas |
| Interface real | quatro grafos conferidos, com 2/2/2/4 agentes reais e retornos expansíveis |
| Persistência e SSE | IDs únicos, respostas e projeções persistidas, replay SSE reconciliado |
| Piloto: seis casos × três arquiteturas | 18 conclusões técnicas, sem sobreposição de tentativas |
| Requisições físicas do piloto | 73 IDs únicos; 85.978 tokens de entrada + 11.885 de saída = 97.863 |
| Contrato arquitetural do piloto | 17 conformidades; uma omissão de delegação preservada e inelegível para sucesso de tarefa |
| Limites do piloto | todos dentro de 20 requisições, 20 consultas e 180 segundos; teto central/swarm de seis respeitado |

Os testes com respostas controladas executam o `strands.Agent` da versão instalada, em vez de substituir subagentes por retornos determinísticos. Conferem acesso exclusivo do especialista à fonte, retorno ao supervisor antes da resposta final, contextos sem gabarito, isolamento entre tentativas e requisições físicas sem soma duplicada de métricas dos pais.

A aplicação real foi validada pela API com `comparisonProtocol=architectural-comparison-v4.2`, callbacks persistidos, fontes controladas, eventos de modelo e interface. O teste é separado do transporte do benchmark. O caminho live sem protocolo também usa o mecanismo comum, com perfil de fontes da aplicação identificado; sua estrutura foi verificada em testes controlados. Os tempos de integração não entram nas medidas do coletor científico.

## Correções durante a validação

O primeiro verificador da integração exigia que **todas** as consultas FAQ tivessem o tópico obrigatório. No exemplo de múltiplas fontes houve uma consulta correta de horário e outra consulta adicional sobre estoque. A regra foi corrigida para exigir pelo menos uma consulta autêntica com argumento e retorno corretos para cada fonte obrigatória. Os registros originais e o primeiro resultado foram preservados; a revalidação usou os mesmos eventos, sem nova inferência. Duas regressões garantem que consultas adicionais não invalidem uma fonte correta e que um retorno não relacionado não a satisfaça.

Uma condição de corrida entre watchdog e limpeza de processo apareceu como warning em teste. A sinalização/limpeza passou a ser serializada e o watchdog é aguardado antes da limpeza principal. Uma falha real de sinalização gera erro explícito, em vez de sucesso ou warning silencioso. A suíte final passou com warnings tratados como erro, antes do piloto.

As primeiras capturas da interface foram preservadas. As capturas verificadas aguardam o texto de retorno e usam contexto de navegador isolado por caso, evitando estado residual do controle de expansão. Não geram novas respostas.

Após o início do lote principal, uma correção exclusivamente visual passou a contar chamadas de ferramenta por `toolCallId` iniciado, em vez de somar eventos de início e término. TypeScript e as 13 regressões Chromium passaram; os dez contadores de agentes nas quatro execuções API preservadas foram confrontados com os eventos e conferem. As novas capturas estão em `ui-tool-counts-verified`, sem inferência adicional. Nenhum código do runtime, coletor, julgador, fonte, parâmetro ou plano congelado do benchmark mudou.

A página adicional `/research/comparison-v42` importa apenas a exportação pública completa, mantendo a centralizada histórica identificada como agente único. A página exige inventário, hashes, proveniência, 600 combinações únicas e reconciliação dos denominadores; antes disso mostra estado pendente. Downloads têm lista fixa de arquivos públicos. TypeScript e nove testes de compatibilidade/privacidade passaram, usando fixtures sintéticas e os metadados estáticos reais congelados. Os módulos de pesquisa preexistentes não foram alterados. Essas verificações de apresentação ocorreram no mesmo host durante parte da geração, sem inferência paralela; não foi medida sistematicamente a carga de CPU. A latência local do coletor é sensível à carga do host e não deve ser tratada como latência de produção.

## Decisão de liberação

Auditoria independente dos 18 registros confirmou integridade, instâncias isoladas, ausência de sobreposição, contexto original equivalente, ausência de gabaritos, limites, snapshots e reconciliação de consumo. A coleta foi tecnicamente liberada. A omissão de delegação é um resultado arquitetural observado e não foi corrigida por chamada artificial, substituição da resposta ou ajuste de prompt para favorecer o resultado. O julgamento de conteúdo permanece independente da liberação.

O pacote integral, comandos e capturas ficam em `research-data/private/agents-as-tools-v42/`. Os relatórios anteriores, TCC e Report 6 não foram alterados. As alterações preexistentes da árvore foram registradas e preservadas; o snapshot privado da aplicação contém o código efetivamente validado, sem arquivos de ambiente. A correção necessária de propagação de settings no serviço, já presente na árvore inicial, foi incorporada ao commit da correção; as demais alterações preexistentes permanecem fora dele.

Pendência preexistente de apresentação: ao abrir uma conversa criada externamente ao fluxo WhatsApp, cabeçalho/composer podem manter o rótulo padrão de arquitetura. O registro de execução e o grafo utilizam a arquitetura realmente executada. Essa limitação está identificada nas evidências e não modifica o despacho ou o lote científico.
