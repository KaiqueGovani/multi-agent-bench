# MAB no WhatsApp Web — extensão 0.3.5

Cada mensagem recebida de texto pode ganhar a ação **Sugerir resposta · MAB**. A solicitação é processada pelo MAB local e a sugestão aparece diretamente abaixo da mensagem escolhida. O fluxo não abre abas de revisão nem painéis flutuantes e não envia mensagens ao WhatsApp.

## Instalar ou atualizar

1. Inicie API, runtime e interface do MAB. O padrão é API `http://127.0.0.1:8000` e interface `http://127.0.0.1:3100`. Bedrock é configurado somente no servidor.
2. No Chrome, abra `chrome://extensions`, ative **Modo do desenvolvedor** e use **Carregar sem compactação**. Selecione esta pasta `extensions/whatsapp-mab`.
3. Para atualizar, use **Recarregar** na extensão e **depois recarregue a página do WhatsApp Web**. Confira a versão **0.3.5** e ative o MAB novamente pelo ícone. Recarregar somente a extensão deixa instâncias antigas na página, podendo duplicar ações ou produzir o erro “Extension context invalidated”.
4. Abra uma conversa de teste e clique no ícone MAB para ativar as ações nas mensagens recebidas. Clique novamente no ícone para desativá-las.

A chave da API usa `chrome.storage.session`. Fechar o Chrome, desabilitar, recarregar ou atualizar a extensão pode limpar essa sessão. Se necessário, use **Ajustar solicitação e conferir contexto → Configurar conexão local**, no cartão, ou **Opções da extensão**, no Chrome, para informar a chave **da API do MAB**. Essa configuração abre uma página interna isolada; a chave não entra no DOM do WhatsApp. Não informe uma chave Bedrock: o formulário a rejeita.

## Fluxo do atendente

1. Abra a conversa e carregue o histórico necessário. A extensão não rola nem consulta APIs ou bancos internos do WhatsApp.
2. Clique em **Sugerir resposta · MAB** abaixo da mensagem recebida que deseja responder. Um cartão compacto abre logo abaixo dessa mensagem. Essa ação ainda não envia o trecho ao servidor.
3. Escolha a arquitetura e o contexto: **Últimas 10 mensagens** ou **Só esta solicitação**. Marcadores verdes aparecem nas mensagens originais que compõem o trecho: **Será enviada · contexto** para as anteriores e **Solicitação selecionada** para o alvo. O corte fica exatamente na mensagem escolhida; mensagens posteriores não entram. O cartão informa quantas mensagens estão no trecho e quantas estão marcadas na conversa.
4. Em **Ajustar solicitação e conferir contexto**, confira o trecho e, se necessário, ajuste a solicitação. Nesse caso, o marcador do alvo acrescenta **Texto ajustado no MAB**, pois será usada a versão editada, sem alterar a bolha original do WhatsApp. O padrão é **Real · Bedrock**; o modo simulado está nas opções.
5. Clique em **Gerar sugestão**. O cartão mostra imediatamente o envio do trecho e depois o processamento no MAB. Durante a espera, há um indicador animado discreto e o estado de cada arquitetura, com a contagem das execuções finalizadas. Os estados vêm do MAB; não há porcentagem ou previsão de tempo. A resposta aparece no mesmo cartão; uma comparação tem abas para as três arquiteturas. Falhas e necessidade de revisão profissional ficam identificadas por arquitetura.
6. Revise a resposta da arquitetura selecionada e use **Inserir na conversa** para preencher a caixa de mensagem do WhatsApp. Se já houver um rascunho, a sugestão é acrescentada ao final, separada por uma linha em branco. A extensão confere que a conversa continua aberta e nunca aciona o envio. **Copiar resposta** continua disponível; **Detalhes no MAB** abre a execução completa apenas quando solicitado.

A inserção fica disponível somente para uma resposta concluída. Ela conserva as quebras de linha, confere a conversa antes e depois do foco e não substitui o rascunho existente. Se o campo não puder ser identificado com segurança, ou o rascunho contiver apenas imagem/emoji como elemento especial, a extensão mantém o conteúdo e orienta a cópia manual. Uma falha parcial pede que o atendente confira o rascunho antes de tentar de novo.

Os campos de ajuste e seleção usam controles nativos que preservam a digitação dentro do cartão, sem transferir o foco para o compositor do WhatsApp.

Os marcadores acompanham a seleção de contexto e são removidos quando o cartão é fechado, a extensão é desativada ou a conversa muda. Eles não alteram o texto das mensagens e não entram na captura. Se uma mensagem selecionada deixar de estar renderizada, o contador distingue o total do trecho das marcações visíveis; o preview continua disponível.

Se o acompanhamento falhar ou atingir seu limite de espera, o indicador para e o cartão orienta retomar. O botão de nova tentativa recupera a mesma importação, sem disparar uma nova execução deliberadamente. Uma resposta parcial já concluída pode ser revisada enquanto as demais arquiteturas continuam processando.

Há apenas um cartão expandido por vez. Fechar o cartão interrompe o acompanhamento local, mas não cancela uma execução aceita pelo servidor. Reabrir a mesma mensagem preserva a tentativa, a importação e a sugestão enquanto o contexto está em memória (até dez cartões por conversa). Se uma resposta da API se perder, **Tentar novamente** mantém o `captureId` para evitar dupla importação. **Nova sugestão** cria uma nova identificação deliberadamente e pode gerar novo consumo.

Mensagens recém-renderizadas recebem a ação enquanto a extensão estiver ativada. Quando a conversa muda, cartões, contexto e resultados anteriores são invalidados. A identidade acessível do campo de composição distingue contatos com o mesmo nome e é usada apenas em memória, sem ser enviada ou armazenada. Mensagens enviadas pelo atendente, participantes não reconhecidos e anexos sem texto não recebem a ação.

## Limites e permissões

- O contexto padrão tem até dez mensagens, sempre terminando na solicitação escolhida. A API admite 200 mensagens, 8.000 caracteres por mensagem e 64.000 no prefixo enviado.
- Recebidas são cliente e enviadas são atendente. Grupos exigem revisão manual. Se o participante não puder ser reconhecido, não é criada uma ação automática para aquela mensagem.
- Imagens, PDFs e áudios não são lidos ou enviados. Uma mídia com legenda pode fornecer somente seu texto; não há OCR nem transcrição.
- Horários locais do WhatsApp não são convertidos para UTC sem informação de fuso confiável.
- `activeTab` + `scripting`: leitura pontual do DOM, no mundo isolado, ativada pelo usuário em `web.whatsapp.com`.
- `storage`: chave local na sessão da extensão, nunca `sync`. A chave fica no background/página de configuração e não é devolvida ao script da conversa. Bedrock permanece no servidor.
- Hosts `http://127.0.0.1/*` e `http://localhost/*`: conexão com a API local. Padrões do Chrome não restringem portas; o formulário aceita somente essas origens em HTTP, sem credenciais, caminhos ou parâmetros.
- Sem permissão permanente de host para WhatsApp, cookies, histórico, `debugger`, APIs privadas, código remoto, telemetria ou coleta de mensagens ausentes.
- As sugestões usam fontes controladas do protótipo, não um ERP real. As novas demonstrações não alteram a coleta experimental congelada.

Os controles e as respostas da extensão são explicitamente excluídos da extração. Uma atualização do layout do WhatsApp pode exigir ajustes nos seletores. O extrator cobre `#main [data-id]`, rótulos acessíveis de remetente, `.selectable-text` e classes legadas. Ele não inventa mensagens ou participantes quando faltam dados.

A edição usa comandos nativos de texto e quebra de linha, sem simular a tecla Enter. `execCommand` é uma API legada específica do navegador e é verificada em Chrome; se ela falhar, não há substituição direta do DOM. Referência: [MDN — execCommand](https://developer.mozilla.org/en-US/docs/Web/API/Document/execCommand).

Documentação primária: [activeTab](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab), [scripting](https://developer.chrome.com/docs/extensions/reference/api/scripting), [storage.session](https://developer.chrome.com/docs/extensions/reference/api/storage).

## Testes locais

```sh
cd extensions/whatsapp-mab
npm ci
npm test
```

Os testes usam dados fictícios e DOM estático, sem abrir sua conta, enviar mensagens ou chamar Bedrock. Cobrem captura atual/legada, exclusão de controles, texto/mídia, papéis, limites, corte/edição, contexto recente, respostas por run, estados de execução, RPC/credenciais, ações por mensagem, marcadores equivalentes ao prefixo enviado, alvo editado, exclusão de mensagens futuras, novo conteúdo renderizado, virtualização, identidade da conversa, fechamento/reabertura idempotente, erro visível, cópia explícita, inserção no compositor com preservação do rascunho, bloqueio após troca de conversa e descarte de respostas atrasadas. Há também testes de regressão dos componentes anteriores mantidos no código. A validação na conta real é uma etapa adicional.

`linkedom` é dependência de desenvolvimento: não é necessário instalar npm para carregar a extensão.

Contrato: `POST /integrations/whatsapp/import`, com `source=whatsapp_web`, `captureId`, `targetSourceId`, `chatTitle`, `messages`, `architectureMode` e `runtimeMode`. O acompanhamento usa `GET /conversations/{conversationId}` e filtra somente os `runIds` retornados. Mensagens históricas do atendente não são confundidas com respostas do modelo.
