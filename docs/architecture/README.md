# Variações da arquitetura do MAB

Cinco candidatas para a Figura 9 e uma figura complementar para a stack tecnológica. Cada diagrama está disponível em SVG vetorial e PNG de alta resolução.

| Variação | Ênfase | Arquivos |
| --- | --- | --- |
| **01 · Visão geral** | Dois percursos em faixas horizontais. Mantém visíveis os serviços e os destinos de persistência da figura de partida. | [SVG](01-visao-geral.svg) · [PNG](01-visao-geral.png) |
| **02 · Dois percursos, um núcleo** | Evidencia onde a aplicação interativa e a coleta direta convergem. Organiza as três arquiteturas no núcleo. | [SVG](02-dois-percursos.svg) · [PNG](02-dois-percursos.png) |
| **03 · Camadas e adaptadores** | Separa entrada, adaptação, execução, dados e serviços. Inclui a extensão do WhatsApp Web como canal. | [SVG](03-camadas-e-adaptadores.svg) · [PNG](03-camadas-e-adaptadores.png) |
| **04 · Raias de execução** | Mostra a ordem das interações, a ida e a volta de eventos e os diferentes pontos de entrada. | [SVG](04-raias-da-execucao.svg) · [PNG](04-raias-da-execucao.png) |
| **05 · Fronteiras da medição** | Distingue latência do núcleo, latência do coletor e julgamento posterior. | [SVG](05-fronteiras-de-medicao.svg) · [PNG](05-fronteiras-de-medicao.png) |
| **06 · Stack tecnológica** | Associa tecnologias a componentes e distingue infraestrutura da aplicação e curadoria da base. | [SVG](06-stack-tecnologica.svg) · [PNG](06-stack-tecnologica.png) |

[Ver a prévia comparativa](previa-comparativa.png)

## Legendas para o manuscrito

**Figura 9** · Serviços da plataforma e percurso direto utilizado na coleta experimental v4.4. Fonte: elaboração própria a partir do código e do protocolo experimental do MAB.

**Figura 10** · Tecnologias utilizadas por componente da plataforma, na infraestrutura local e na curadoria dos dados. Fonte: elaboração própria com ícones do Devicon, do Strands Agents e do AWS Architecture Icons.

## Referências técnicas

- Os serviços da aplicação seguem o capítulo de desenvolvimento. O Docker Compose local inicia PostgreSQL e MinIO. A stack mostra SQLite na preparação dos dados de pesquisa. [Desenvolvimento](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/docs/tcc/manuscript/06-desenvolvimento.md) · [Docker Compose](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/infra/docker/docker-compose.yml)
- O coletor usa o núcleo diretamente em subprocessos e grava resultados locais. A latência do núcleo e a do coletor são medidas distintas. O julgamento ocorre após a geração. [Protocolo v4.4](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/experiments/architectural-comparison-v44/README.md) · [Relatório v4.4](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/research-data/results/architectural-comparison-v44/RELATORIO.md)
- O runtime mantém adaptadores de domínio para a aplicação e fontes controladas na pesquisa. O adaptador da POC usa dados controlados e trabalha com descritores de anexos. [Runtime](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/apps/agent-runtime/app/services/execution.py) · [Adaptadores da POC](https://github.com/KaiqueGovani/multi-agent-bench/blob/803d9d7c321aaab68593925e0583d9a0be3629b5/apps/agent-runtime/app/tools/application_tools.py)
- Os nove ícones da Figura 10 do DOCX de 03/11/2026 foram reutilizados. Os ícones de SQLite e Amazon Bedrock completam a nova figura. [Devicon 2.17.0](https://github.com/devicons/devicon/tree/v2.17.0) · [Strands Agents](https://strandsagents.com/docs/) · [AWS Architecture Icons](https://aws.amazon.com/architecture/icons/)
