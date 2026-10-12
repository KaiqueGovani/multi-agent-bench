# Fontes do diagrama arquitetural

Diagrama autoral gerado a partir de código/configuração, não de uma captura de execução HTTP. Os IDs abaixo aparecem no SVG e no PNG. Caminhos relativos à raiz do repositório `multi-agent-bench`; commit examinado `3fa15c4140fc701edf1967f1217576cebdd106cf` mais a nova rota de apresentação descrita no relatório.

| ID | Elemento comprovado | Código/configuração |
|---|---|---|
| A1 | Frontend Next.js: chat, dashboard, inspeção | `apps/web/package.json`; `apps/web/src/app/page.tsx`; `apps/web/src/app/dashboard/page.tsx`; `apps/web/src/components/runtime/run-execution-panel.tsx` |
| A2 | FastAPI transacional e rotas de leitura | `apps/api/app/main.py`; `apps/api/app/api/routes/__init__.py`; `apps/api/app/api/routes/runs.py` |
| A3 | PostgreSQL e entidades de atendimento/eventos/projeções | `apps/api/app/db/models.py`; `apps/api/app/db/session.py`; `infra/docker/docker-compose.yml` |
| A4 | Anexos locais ou S3/MinIO configurável | `apps/api/app/adapters/storage/__init__.py`; `local.py`; `s3.py`; `apps/api/app/core/config.py`; `infra/docker/docker-compose.yml` |
| A5 | Persistência da projeção e eventos da plataforma | `apps/api/app/services/run_execution.py` |
| A6 | Entrada HTTP do runtime e aceitação de processamento | `apps/agent-runtime/app/main.py`; `apps/agent-runtime/app/schemas/runtime.py` |
| A7 | Seleção da arquitetura e execução direta do núcleo | `apps/agent-runtime/app/services/execution.py`; `apps/agent-runtime/app/architectures/comparison.py` |
| A8 | Strands Agent, BedrockModel e Bedrock Converse; juiz via boto3 | `apps/agent-runtime/app/architectures/comparison.py` (ControlledAgent/RecordedBedrockModel); `scripts/judge_automated_pilots.py` (converse); SDK instalado `strands/models/bedrock.py` (Converse quando streaming=False) |
| A9 | Ferramentas controladas e limites dos descritores | `apps/agent-runtime/app/tools/research_tools.py`; `apps/agent-runtime/app/tools/domain_tools.py` |
| A10 | Plano congelado e execução em subprocessos | `scripts/run_research_pilot.py`; `manifest.json` e `execution-order.csv` do lote privado preservado |
| A11 | Resultados/eventos e exportações originais em arquivos | `scripts/run_research_pilot.py` (LocalEvents, worker, result.json, exports) |
| A12 | Avaliação principal técnica, verificação objetiva e rechecagem | `scripts/judge_automated_pilots.py`; `apps/agent-runtime/app/experiments/methodology.py`; registros de avaliações/rechecagem do lote |
| A13 | Cópia local de apresentação posterior à coleta | `scripts/preparar.py`, `servidor.py`, `visualizacao.html` deste pacote; nova rota `apps/web/src/app/research-captures/page.tsx` |

| ID | Ligação | Sustentação |
|---|---|---|
| L1 | Frontend → API por HTTP; consumo SSE | `apps/web/src/lib/api/client.ts`; rotas `runs.py` e `events.py` da API |
| L2 | API → PostgreSQL via SQLAlchemy | `apps/api/app/db/session.py`; serviços `runs.py`, `messages.py`, `run_execution.py` |
| L3 | API → adapter de anexos | `apps/api/app/api/routes/attachments.py`; `apps/api/app/adapters/storage/__init__.py` |
| L4 | API → runtime e callbacks de retorno | `apps/api/app/services/processing_dispatcher.py`; `apps/agent-runtime/app/services/callbacks.py`; `apps/api/app/api/routes/integrations.py`; PATCH em `runs.py` |
| L5 | Runtime HTTP → executor | `apps/agent-runtime/app/main.py`; `apps/agent-runtime/app/services/execution.py` |
| L6 | Núcleo → Strands → Bedrock Converse | `apps/agent-runtime/app/architectures/comparison.py`; implementação instalada de `strands.models.bedrock.BedrockModel` |
| L7 | Agentes → fontes controladas | `apps/agent-runtime/app/architectures/comparison.py`; `apps/agent-runtime/app/tools/research_tools.py` |
| L8 | Plano → núcleo por processo, sem API/DB ao vivo | `scripts/run_research_pilot.py` (worker/RuntimeExecutor/subprocess.Popen) |
| L9 | Núcleo → arquivos de evento/resultado | `scripts/run_research_pilot.py` (LocalEvents, result.json) |
| L10 | Arquivos → verificador objetivo e juiz | `scripts/judge_automated_pilots.py`; `apps/agent-runtime/app/experiments/methodology.py` |
| L11 | Registros → cópia de apresentação | `scripts/preparar.py` deste pacote (importação SQLite idempotente) |
| L12 | Juiz → Bedrock Converse via boto3 | `scripts/judge_automated_pilots.py` (client.converse, modelo Sonnet 4.5); `judge-config.json` original |
| L13 | Cópia de apresentação → nova rota do frontend | `scripts/research-captures-page.tsx` deste pacote; `apps/web/src/app/research-captures/page.tsx` |

A seta L4 descreve uma capacidade implementada. Ela não ocorreu durante a coleta definitiva. PostgreSQL, SSE interativo e anexos S3/MinIO também não foram exercitados como serviços ao vivo nesse lote. Não há seta das ferramentas experimentais para o banco de atendimento: FAQ, estoque e descritores usam fontes controladas. O juiz usa boto3 diretamente; não passa pelo agente Strands da geração.
