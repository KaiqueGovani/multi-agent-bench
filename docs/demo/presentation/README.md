# MAB em execução

Material para a reunião de orientação de 4 de novembro de 2026. O PDF reúne 16 capturas do navegador, uma por página. São cinco do WhatsApp Web, oito do chat do MAB com a interface atualizada e três do painel de pesquisa v4.4.

| Arquivo | O que abrir na reunião |
| --- | --- |
| [Prints da demonstração prática](prints-demonstracao-pratica.pdf) | Integração WhatsApp Web → MAB → rascunho, chat e rastreamento do MAB, e painel de pesquisa. |
| [Sequência de prints do WhatsApp e MAB](whatsapp-sequencia.gif) | GIF montado com cinco capturas do navegador, da revisão da pergunta ao rascunho. |
| [Vídeo do chat do MAB](mab-demonstracao.mp4) | Acompanhar a mensagem de teste, o fluxo animado, os eventos e os detalhes de uma etapa. O vídeo tem 21 segundos. |
| [Vídeo do painel v4.4](resultados-navegacao.mp4) | Abrir a comparação, navegar por resultados, contrastes e gráficos, e baixar um arquivo da coleta. |

No teste da integração, a extensão rodou no WhatsApp Web conectado à API local. O cartão encaminhou somente a cópia revisada da solicitação, com uma pergunta fictícia. As três arquiteturas concluíram e a conversa abriu no MAB pelo botão de detalhes. A resposta selecionada foi inserida no compositor. O rascunho de teste foi removido após a captura e nenhuma mensagem foi enviada ao contato. Os recortes excluem o nome e o histórico da conversa. [Guia da extensão](../whatsapp.md)

O novo vídeo e os oito prints do chat foram gravados após o polimento do front-end, com uma mensagem de teste nas três arquiteturas. O fluxo e a aba Atividade receberam eventos da API local via SSE. A integração e o chat usam a API FastAPI e um banco PostgreSQL de demonstração, com runtime simulado. Os tempos registrados no vídeo pertencem à sessão de demonstração.

O painel roda localmente com os artefatos sanitizados da v4.4. São 600 tentativas, com 40 cenários, cinco repetições e três arquiteturas. A avaliação de conteúdo é automática e a revisão humana está pendente. Para abrir o painel a partir do repositório, use `npm ci --prefix apps/web` e `make research-results`, depois acesse `/research/comparison-v44` no servidor local. [Relatório da coleta v4.4](../../../research-data/results/architectural-comparison-v44/RELATORIO.md)
