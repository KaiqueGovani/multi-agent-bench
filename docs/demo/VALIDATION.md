# Validação local — WhatsApp → MAB

Data: 31 de outubro de 2026. Verificação funcional do adaptador e do fluxo do atendente; não integra nem substitui a coleta científica congelada.

## Testes automatizados

- API: 46 testes aprovados, incluindo 23 novos testes de importação WhatsApp.
- Runtime: 165 testes aprovados.
- Extensão 0.3.5: 68 testes aprovados com DOM fictício, incluindo o formato de seletores observado na sessão atual do WhatsApp, ações por mensagem recebida, respostas abaixo da solicitação, cópia, trocas de contato, linhas virtualizadas, cache de execuções, controles de edição nativos, isolamento de eventos e RPC.
- Interface: testes E2E `whatsapp-attendant.spec.ts`, `whatsapp-native-editor.spec.ts`, `whatsapp-context-marker.spec.ts`, `whatsapp-insert-reply.spec.ts` e `whatsapp-progress.spec.ts` aprovados. Conferem preservação do histórico ao alternar arquitetura, cópia da sugestão, continuação real de uma captura iniciada como simulada e foco de edição no Chrome. O segundo teste reproduz um listener global que rouba o foco de elementos não nativos e preserva um rascunho preexistente.
- TypeScript: `npm run typecheck` aprovado.
- `git diff --check`: sem problemas.

Esses testes usam dados fictícios e não fazem inferência remota. Os testes do runtime simulam o provedor e verificam também falha sem retorno artificial.

## Inferência real e persistência

API e runtime locais em 8000/8010, interface em 3100. PostgreSQL 16 em banco de demonstração separado, com as migrações até `20260429_0003`. Gerador Claude Haiku 4.5 via Bedrock, região `us-west-2`, protocolo `architectural-comparison-v4.1`.

1. Importação técnica de duas mensagens fictícias: três execuções reais concluídas e três respostas persistidas. Repetir o mesmo payload recuperou as mesmas execuções, sem duplicação.
2. Extensão carregada manualmente pelo autor no Chrome, após autorização. Foi aberta a conversa de teste indicada. Na revisão, o autor manteve somente a solicitação selecionada e substituiu seu texto por uma pergunta fictícia sobre estoque de dipirona.
3. O envio pela extensão abriu a conversa correta no MAB. A conferência pela API mostrou uma única mensagem importada como cliente, com o texto fictício esperado. As três arquiteturas terminaram com `completed`, protocolo correto, três respostas persistidas e zero erros de ferramenta.
4. O navegador mostrou a pergunta revisada, os seletores das três arquiteturas e a resposta. A troca de arquitetura e a cópia da sugestão foram verificadas; nenhuma mensagem foi enviada ao contato.

As etapas de instalação e envio da revisão foram executadas pelo autor: o controle automático não acessava o gerenciador de extensões, e o controle nativo estava sem permissão. A conferência dos registros, respostas e cópia no MAB foi realizada pelo agente.

Evidências individuais e capturas ficam em `var/whatsapp-demo/`, ignorado pelo Git. A chave temporária está somente na configuração local ignorada do runtime; o ZIP da extensão não contém credenciais ou dados de conversas.

## Limites

A captura reflete somente mensagens renderizadas na conversa aberta. Não há API oficial de integração com WhatsApp, coleta em segundo plano, leitura de mídias ou envio automático ao contato. A resposta usa fontes controladas do protótipo e depende de revisão pelo atendente. A geração interativa pode despachar arquiteturas em paralelo; seus tempos não devem ser apresentados como reprodução do protocolo sequencial da coleta. Os testes não constituem validação farmacêutica.

## Correção de foco e chamada de rede — 0.3.2

O problema de digitação foi reproduzido no WhatsApp atual: o foco saía do textarea no Shadow DOM e era redirecionado ao compositor. Os controles foram movidos para o DOM principal, mantendo a apresentação por slots e bloqueando a propagação dos eventos próprios sem impedir sua edição nativa. Após a correção, a digitação real de uma pergunta fictícia permaneceu no textarea e o rascunho do WhatsApp ficou idêntico. O marcador da reprodução foi removido, sem envio ao contato.

Também foi corrigido o receptor da chamada `fetch` no service worker; o método padrão é vinculado ao escopo global. Um teste de regressão reproduz a invocação incorreta anterior. Os 47 testes da extensão passam.

Após atualizações durante desenvolvimento, a aba do WhatsApp precisa ser atualizada para remover scripts de versões anteriores ainda presentes. Na página limpa, as ações foram reativadas e a chamada da extensão chegou à API, que respondeu HTTP 401 por falta ou divergência da chave local. A geração nessa nova apresentação depende de reconfigurar a chave da API MAB na extensão. A geração real nas três arquiteturas já foi conferida na primeira integração descrita acima; não se presume que isso valide automaticamente a nova apresentação por mensagem.

## Marcadores de contexto — 0.3.3

Marcadores são adicionados às mensagens originais selecionadas pelo mesmo `selectContext` usado no envio. O alvo é distinguido do histórico e recebe aviso quando o texto da cópia é ajustado no MAB. A legenda informa o total selecionado e o total de linhas atualmente marcadas. Fechamento, troca de contexto/solicitação, troca de conversa e linhas recicladas removem ou reconciliam os marcadores, sem modificar o texto das mensagens. Os próprios marcadores ficam excluídos da extração.

Testes em Chrome com conversa fictícia compararam os IDs marcados ao payload produzido pelo construtor real de importação: dez mensagens recentes, somente alvo, texto ajustado, exclusão de mensagens posteriores, limpeza ao fechar e reabertura do cartão. A regressão de foco também passou. A captura `var/whatsapp-demo/context-markers-preview.png` é apenas dessa conversa fictícia, sem dados do WhatsApp do autor nem chamadas externas. A aplicação dos marcadores na sessão atual depende de instalar/recarregar a versão 0.3.3 e atualizar a aba do WhatsApp.

## Inserção no rascunho — 0.3.4

O botão **Inserir na conversa** usa a resposta concluída da arquitetura selecionada. O clique confere a identidade da conversa, localiza um único compositor nativo visível e revalida o contexto após focar e antes de editar. A sugestão é acrescentada ao rascunho existente, com separação por linha em branco, sem simular Enter ou acionar envio. Imagens/decoradores sem texto no rascunho são preservados e solicitam cópia manual; falhas não provocam tentativas automáticas.

A estrutura do compositor da sessão atual foi conferida por leitura do DOM: campo nativo editável com papel textbox e editor Lexical. A validação de inserção usa um compositor fictício em Chrome com os scripts de produção e RPC simulado, sem acessar conta ou modelo. A ativação na conta do autor ainda requer recarregar a extensão 0.3.4, atualizar a página do WhatsApp e clicar no MAB.

Na 0.3.4, os 64 testes unitários da extensão passaram. Os três casos do novo teste Chrome passaram: resposta multilinha com rascunho existente, campo vazio e rascunho somente com emoji/imagem preservado com orientação de cópia. Os testes conferem literalmente as quebras de linha, a atualização do modelo pelo evento nativo de edição, a aba de arquitetura escolhida, o bloqueio após troca de conversa e zero envios. `npm run typecheck` também passou.

## Indicadores de progresso — 0.3.5

O cartão exibe imediatamente **Enviando trecho**, seguido de **Processando no MAB**. Há um indicador de atividade nas fases de envio/processamento, estado por arquitetura e contagem de execuções finalizadas. Fila, execução, conclusão, falha, cancelamento, ausência de resposta e revisão profissional são distinguidos com base nos dados recebidos. Não se apresenta porcentagem nem previsão de tempo.

Erro de rede e limite de espera interrompem a animação e permitem retomar as mesmas execuções. Fechamento, desativação e troca de conversa limpam timers e descartam retornos antigos; nova sugestão limpa os indicadores. O botão informa `aria-busy`, os anúncios de progresso ficam fora da região ocupada, estados repetidos não recriam anúncios e a animação respeita preferência por movimento reduzido.

Os testes Chrome `whatsapp-progress.spec.ts` e `whatsapp-insert-reply.spec.ts` passaram juntos (seis casos), usando dados fictícios e RPC simulado. Conferem envio com resposta adiada, fila, parcial 1/3, conclusão com falha, erro de polling, timeout virtual, retomada sem nova importação, reabertura, descarte de retorno após troca de conversa e preservação da inserção no rascunho. TypeScript passou. A prévia `var/whatsapp-demo/progress-preview.png` mostra apenas uma conversa fictícia e foi revisada visualmente. A ativação na conta requer recarregar a extensão 0.3.5 e atualizar a página do WhatsApp.

A suíte da extensão 0.3.5 passou com 68 testes, incluindo quatro novos testes do ciclo de progresso: estados parciais/terminais, preservação dos nós quando o estado é idêntico, erro/retomada sem nova importação, pausa/reabertura e descarte de callbacks antigos. Checagem de sintaxe JavaScript e `git diff --check` sem problemas.
