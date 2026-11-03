# Demonstração WhatsApp → MAB

O atendente captura manualmente a conversa aberta, revisa o trecho, escolhe uma arquitetura e consulta uma sugestão no MAB. O envio ao contato é manual. A comparação interativa despacha as arquiteturas em paralelo. As métricas da coleta científica ficam na [comparação v4.4](../../research-data/results/architectural-comparison-v44/RELATORIO.md).

## Iniciar os serviços

Instale as dependências de cada serviço com `uv sync --all-extras` em `apps/api` e `apps/agent-runtime`, e `npm ci` em `apps/web`. Configure o runtime em `apps/agent-runtime/.env`: `ENABLE_LIVE_LLM=true`, `AWS_REGION=us-west-2`, modelo Haiku usado no estudo e `AWS_BEARER_TOKEN_BEDROCK`. A credencial Bedrock não pertence à extensão.

Com PostgreSQL acessível e migrações aplicadas, inicie os serviços em três terminais. Configure `DATABASE_URL` para um banco de demonstração e defina `MAB_API_KEY` e `MAB_RUNTIME_SECRET` com valores locais.

```sh
# Terminal 1, apps/agent-runtime
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8010

# Terminal 2, apps/api; substitua os valores pela configuração local
DATABASE_URL="$DATABASE_URL" \
API_KEY="$MAB_API_KEY" AI_SERVICE_SECRET="$MAB_RUNTIME_SECRET" \
RUNTIME_MODE=real AI_RUNTIME_URL=http://127.0.0.1:8010 \
APP_BASE_URL=http://127.0.0.1:8000 \
CORS_ALLOWED_ORIGINS=http://127.0.0.1:3100,http://localhost:3100 \
.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 3, apps/web
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000 \
NEXT_PUBLIC_API_KEY="$MAB_API_KEY" npm run dev -- --hostname 127.0.0.1 --port 3100
```

Use a mesma chave MAB na API, na interface e na extensão. Consulte `/health` na API e no runtime para verificar a configuração. A validade da credencial Bedrock é confirmada na primeira chamada ao provedor.

## Usar dentro do WhatsApp

1. Instale ou recarregue a pasta `extensions/whatsapp-mab` no gerenciador do Chrome. Abra o WhatsApp Web, selecione o contato normalmente e clique na extensão para ativar as ações.
2. Cada mensagem de texto recebida passa a ter **Sugerir resposta · MAB** logo abaixo. Clique na ação da solicitação que deseja responder.
3. O cartão abre abaixo dessa mesma mensagem. Escolha a arquitetura e **Últimas 10 mensagens** ou **Só esta solicitação**. As mensagens incluídas recebem um marcador na própria conversa: **Será enviada · contexto** para o histórico e **Solicitação selecionada** para o alvo. A legenda do cartão informa o total e quantas estão marcadas na área renderizada. Só então clique **Gerar sugestão**. Mensagens posteriores ao alvo não entram no contexto.
4. Logo após o clique, o cartão mostra **Enviando trecho** e depois o processamento, com indicador de atividade, estado de cada arquitetura e contagem das execuções finalizadas. As informações vêm do MAB, sem porcentagem ou previsão artificial. Em falhas, o indicador para e permite retomar o acompanhamento. A resposta aparece no próprio cartão. Ao comparar as três arquiteturas, alterne entre suas abas. **Inserir na conversa** coloca a resposta da aba selecionada na caixa de mensagem do WhatsApp para revisão. Se houver um rascunho, ele é preservado e a sugestão é acrescentada ao final. A ação confere a conversa aberta; nenhum botão envia ao contato. **Copiar resposta** continua disponível. **Detalhes no MAB** é opcional.
5. **Ajustar solicitação e conferir contexto** permite revisar os textos e escolher o modo real/simulado. Para um teste sem histórico pessoal, use **Só esta solicitação** e substitua o texto da cópia por `Vocês têm dipirona em estoque?`. Isso não altera a mensagem original do contato; o marcador do alvo passa a avisar **Texto ajustado no MAB**, e a prévia mostra o texto efetivamente selecionado.

O cartão e as ações acompanham a conversa e suas mensagens renderizadas. Ao trocar de contato ou remover a mensagem da área carregada, o acompanhamento anterior é interrompido. Somente um cartão fica aberto por vez. Os marcadores acompanham a seleção e desaparecem ao fechar o cartão, desativar a extensão ou trocar de conversa. Não é necessário abrir o painel flutuante ou uma nova aba de revisão no percurso principal.

**Conexão inicial:** dentro das opções do cartão, **Configurar conexão local** abre uma página confiável da extensão para informar a chave da API MAB e os endereços acima. Essa configuração mantém a chave fora do DOM do WhatsApp e dura a sessão; atualizar ou recarregar a extensão pode exigir configurá-la novamente. A chave Bedrock fica somente no servidor.

A captura inclui apenas o que o WhatsApp renderizou; não exporta a conversa completa. Mídias não são baixadas ou interpretadas. Repetir uma tentativa mantém a identificação e recupera a importação existente; **Nova sugestão** cria deliberadamente uma nova execução. As conversas importadas são armazenadas no PostgreSQL local. A indicação de avaliação profissional não representa transferência humana executada.

## Validação

```sh
(cd apps/api && .venv/bin/python -m pytest -q)
(cd apps/agent-runtime && .venv/bin/python -m pytest -q)
(cd extensions/whatsapp-mab && npm ci && npm test)
(cd apps/web && npm run typecheck && npm run test:e2e -- whatsapp-attendant.spec.ts --workers=1)
```

Os testes automatizados usam dados fictícios e provedores simulados. A verificação com uma conversa do WhatsApp atual e inferência real é uma etapa separada, documentada no resultado da execução local. Não acrescenta unidades ao experimento científico.
