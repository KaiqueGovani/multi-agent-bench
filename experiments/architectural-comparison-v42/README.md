# Correção da orquestração — protocolo v4.2

Este protocolo substitui a implementação centralizada para uma **nova** comparação. O lote `matrix40-v1-final`, protocolo v4.1, é preservado. Sua centralizada é uma referência de **agente único com ferramentas de domínio**; seus resultados não medem o supervisor multiagente corrigido.

O caminho experimental é `scripts/run_research_pilot.py` → subprocesso isolado → `RuntimeExecutor` → `execute_comparison`. A presença de `experiment.comparisonProtocol` seleciona esse caminho; alterar somente `centralized.py` não modifica a coleta. A aplicação usa o mesmo mecanismo de orquestração, com a ligação de fontes identificada separadamente. Não há ERP, OCR ou transferência humana real.

## Identidade histórica preservada

| Item | Valor |
|---|---|
| Experimento anterior | `485144d5-74d2-4fef-8998-b1629d6d493a` |
| Commit anterior | `e6a638f85502566a9d93e436359e98a292861f77` |
| Manifesto anterior SHA-256 | `921b54f9310e3281c519e5b61100304aa3a4755a27daf0238a96c3910f4cf208` |
| Lista normalizada dos 40 casos SHA-256 | `8c251bec5e78dc6f355840fb89f6e400c3988fa9f68496e31fd25b476b600866` |
| Arquivo original de cenários SHA-256 | `9dd22bdc3e22da4e7d781bcdad2592ec4710cf756436cf134289b2d48c8c19ad` |
| Sistema do julgador SHA-256 | `ac77d9d9800bd6830102e5760a4d848330c3bcfcfa6d65b7d5723713f9478e36` |
| SDK instalado e histórico | Strands Agents `1.37.0` |

Os seis hashes dos assets e os hashes individuais dos 40 casos são conferidos contra o manifesto original. Os casos completos, históricos e gabaritos permanecem no armazenamento restrito. O agente recebe contexto de entrada e política comum, nunca o gabarito.

## Diferenças congeladas

| Aspecto | v4.1 preservada | v4.2 |
|---|---|---|
| Centralizada | supervisor acessa domínio diretamente | supervisor escolhe ferramentas `@tool` que invocam agentes especialistas reais |
| Autoridade final | supervisor | supervisor; sem sintetizador adicional |
| Especialistas | workflow/swarm | fábrica comum às três arquiteturas; competências de domínio preservadas |
| Mínimo de delegação central | inexistente | pelo menos uma invocação de especialista; FAQ para entrada geral |
| Teto central | inexistente | seis invocações de especialistas por tentativa |
| Swarm | até seis delegações | mesmo teto e extensão explícita de delegação entre pares |
| Evidências | ferramentas/atores | ligações de execução, agente pai, ferramenta, chamada física, retorno e contrato arquitetural |
| Consumo | uso do agente e ledger | ledger de requisições físicas únicas como fonte autoritativa; uso SDK apenas diagnóstico |
| Interface | podia exibir especialistas sem execução real | nós e retornos sustentados por eventos de agentes reais |
| Contrato arquitetural | sem campo específico | campo técnico explícito, independente da rubrica semântica |
| Retomada | interrupção podia bloquear avanço | primeira tentativa preservada; executar somente unidades não iniciadas |

Os prompts de domínio, fontes, política de recomendação e papéis do workflow/swarm não devem mudar incidentalmente. Qualquer diferença necessária é registrada com hashes e regressões antes da coleta. A memória do mesmo especialista pode persistir dentro de uma tentativa; não há compartilhamento entre tentativas, arquiteturas ou cenários.

## Configuração

Geração: `us.anthropic.claude-haiku-4-5-20251001-v1:0`, temperatura 0, saída máxima 2.048 tokens. Julgamento: `us.anthropic.claude-sonnet-4-5-20250929-v1:0`, temperatura 0, saída máxima 4.096 tokens. Região `us-west-2`. Sem fallback mock, sem retries automáticos de inferência. Geração e julgamento sequenciais.

Por tentativa, os limites globais incluem chamadas aninhadas: 20 requisições ao modelo, 20 chamadas de domínio e 180 segundos. O encerramento por tempo não permite continuar executando filhos em segundo plano. Uma resposta sem delegação obrigatória é preservada com violação arquitetural; não se acrescenta uma chamada artificial.

O piloto de engenharia tem seis casos sintéticos definidos previamente e uma tentativa por arquitetura (18 unidades), separado do lote principal. A integração real entra pela API e confere persistência e interface; suas medições não integram o benchmark. A liberação depende de arquitetura, isolamento, limites, integração e reconciliação verificáveis, nunca de uma taxa de sucesso favorável.

O novo lote tem 40 cenários × cinco repetições × três arquiteturas = 600 unidades novas. Mantém o transporte subprocesso/núcleo e a ordem em blocos balanceados com semente `20261011`. O tempo histórico `end_to_end_latency_ms` inclui lançamento/importação/arquivos do coletor; `latency_ms` delimita a execução do núcleo. Nenhum desses campos mede a latência da aplicação em produção. Avaliação e integração HTTP têm fronteiras próprias.

## Avaliação e análise

O instrumento semântico do julgador é preservado pelo hash acima. A verificação objetiva procura chamadas de domínio concluídas, argumento correto e retorno íntegro dentro dos especialistas. Consultar um especialista ou alegar consulta no texto não comprova acesso à fonte. Conteúdo, procedimento e contrato arquitetural são campos separados.

O plano operacional está em `analysis-plan.json`, declarado antes de novas respostas. O cenário é a unidade pareada, com suas cinco repetições agrupadas. Diferenças de sucesso são expressas em pontos percentuais, com reamostragem de cenários e três testes pareados corrigidos por Holm. Ausências, julgamentos inválidos, primeiras tentativas e falhas permanecem visíveis. A rechecagem de 15 respostas usa o mesmo juiz e preserva o julgamento principal.

`pricing.json` registra tarifas públicas, data, moeda, região e pressupostos. Custos são estimativas a partir de tokens observados, separados por fase; não representam cobrança efetiva. Não há revisão farmacêutica nem validação clínica. A amostra intencional e conhecida continua limitando a generalização.

## Privacidade e artefatos

O pacote integral fica sob `research-data/private/agents-as-tools-v42/`, ignorado pelo Git e com permissões restritas. Código, testes, protocolo e síntese quantitativa sanitizada podem ser versionados. Não publicar credenciais, mensagens, identificadores pessoais, trajetórias ou gabaritos privados. Relatórios anteriores e o texto do TCC não são substituídos por resultados parciais.

Referência: [Agents as Tools, documentação oficial Strands](https://strandsagents.com/docs/user-guide/sdk/multi-agent/agents-as-tools/). A implementação usa `@tool` compatível com o SDK instalado e mantém instrumentação explícita dos subagentes.
