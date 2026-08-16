# 6 DESENVOLVIMENTO DO SISTEMA

O projeto utiliza uma stack dividida em três frentes principais: backend transacional, frontend web e serviço de execução dos agentes. Essa separação foi adotada para permitir que a interface de atendimento, a persistência dos dados e a execução das arquiteturas multiagentes evoluam de forma modular.

No backend transacional, são utilizados Python, FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, Psycopg, Uvicorn, python-multipart, python-dotenv, Boto3 e SSE-Starlette. Esse conjunto de tecnologias permite criar endpoints REST, validar dados, persistir conversas e mensagens, controlar migrações de banco, armazenar runs, registrar eventos, lidar com anexos e transmitir atualizações em tempo real por Server-Sent Events.

No frontend web, são utilizados Next.js, React, TypeScript, Tailwind CSS, PostCSS, Autoprefixer, lucide-react, motion e @xyflow/react. A interface contempla um workspace de chat, histórico de conversas, envio de mensagens com anexos, timeline operacional, painel de revisão humana, inspeção técnica, dashboard e visualização dos fluxos arquiteturais.

No serviço de execução dos agentes, são utilizados Python, FastAPI, Strands Agents, Strands Agents Tools, Uvicorn, AWS Bedrock em modo live e OpenTelemetry/OTLP para telemetria opcional. Esse serviço é responsável por receber a execução de uma run, selecionar a arquitetura, executar a coordenação entre agentes, acionar ferramentas de domínio e retornar eventos técnicos para a API principal.

Para persistência, é utilizado PostgreSQL como banco relacional principal. Para armazenamento de arquivos, o projeto prevê storage local e compatibilidade com S3, incluindo MinIO em ambiente local. Essa abordagem permite salvar imagens, PDFs e demais anexos do atendimento de forma desacoplada da lógica principal da aplicação.

O projeto também utiliza contratos compartilhados em TypeScript, organizados em um pacote comum, para reduzir divergências entre frontend, backend e serviço de execução dos agentes. Para testes e validação, são utilizados Pytest no backend e no serviço de execução dos agentes, Playwright no frontend e fixtures de teste para cenários reproduzíveis. O ambiente de desenvolvimento também conta com Docker Compose para execução local de serviços auxiliares, como PostgreSQL e MinIO.
