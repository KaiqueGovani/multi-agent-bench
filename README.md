# Multi-Agent Bench

> **Experimental multi-agent system for intelligent pharmacy customer service — comparing coordination architectures through an observable, channel-agnostic POC.**

![Status](https://img.shields.io/badge/status-POC-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![TypeScript](https://img.shields.io/badge/typescript-5.x-blue)
![License](https://img.shields.io/badge/license-Academic-lightgrey)

---

## Overview

This repository hosts the **undergraduate thesis (TCC)** project focused on building a multi-agent system for intelligent pharmacy customer service. The primary research goal is to **compare coordination architectures** between agents in an experimental, observable environment.

### Current Phase: Proof of Concept

The POC establishes the foundational interaction and observability layer:

- ✅ **Multimodal Web Chat** — Text and image input with preview
- ✅ **Real-time Event Streaming** — SSE-based processing timeline
- ✅ **Conversation Persistence** — Messages, attachments, and events stored in PostgreSQL
- ✅ **Mock Runtime** — Simulated agent processing for end-to-end flow validation
- ✅ **Channel-Agnostic Architecture** — Designed for future WhatsApp integration
- ✅ **Observability Ready** — Correlation IDs, tracing, and structured event logging

### Out of Scope (For Now)

- Real agent logic and LLM integrations
- Clinical decision rules and pharmaceutical automation
- Experimental architecture comparisons

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Git

### 1. Clone and Setup

```bash
git clone https://github.com/KaiqueGovani/multi-agent-bench.git
cd multi-agent-bench
```

### 2. Start Infrastructure

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres
```

### 3. Setup Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/Scripts/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -e ./apps/api

# Run migrations
cd apps/api
alembic upgrade head
cd ../..

# Start API server
uvicorn app.main:app --reload --app-dir apps/api
```

### 4. Setup Frontend

```bash
cd apps/web
npm install
npm run dev
```

### 5. Access the Application

| Service | URL |
|---------|-----|
| Web Chat | http://localhost:3000 |
| API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Web Chat (Next.js)                          │
│                    Text + Image Input / Event Timeline              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP Multipart / SSE
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Web Chat Adapter                               │
│              Normalizes channel-specific payloads                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ NormalizedInboundMessage
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Application Layer                              │
│         Conversation Management / Message Processing                │
├─────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌────────────┐  │
│  │  Services   │  │   Runtime   │  │   Storage   │  │  Streaming │  │
│  │             │  │   (Mock)    │  │   Adapter   │  │   (SSE)    │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  └────────────┘  │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  PostgreSQL   │      │  MinIO / S3   │      │  Future:      │
│  Persistence  │      │  Attachments  │      │  WhatsApp     │
└───────────────┘      └───────────────┘      └───────────────┘
```

### Key Design Decisions

- **Channel Independence**: The application core never knows if the message came from Web Chat or WhatsApp
- **Normalized Messages**: All channels transform input into a standard internal format
- **Event-First**: Every processing step emits observable events for debugging and future analysis
- **Run-Based Tracking**: Each agent execution creates a `run` for architecture comparison

---

## Project Structure

```
multi-agent-bench/
├── apps/
│   ├── api/                    # FastAPI backend
│   │   ├── app/
│   │   │   ├── api/routes/     # HTTP & SSE endpoints
│   │   │   ├── adapters/       # Inbound, outbound, storage, streaming
│   │   │   ├── domain/         # Business entities
│   │   │   ├── services/       # Application use cases
│   │   │   ├── runtime/        # Mock agent processing
│   │   │   ├── schemas/        # Pydantic contracts
│   │   │   └── core/           # Config, security, observability
│   │   └── alembic/            # Database migrations
│   │
│   └── web/                    # Next.js frontend
│       └── src/
│           ├── app/            # Pages and layouts
│           ├── components/     # Chat, events, UI primitives
│           ├── hooks/          # React hooks
│           └── lib/            # API client, SSE, utilities
│
├── packages/
│   ├── contracts/              # Shared TypeScript contracts & schemas
│   │   ├── src/                # Enums, domain types, API contracts
│   │   ├── schemas/            # JSON Schema definitions
│   │   └── examples/           # Sample payloads
│   │
│   └── test-fixtures/          # Test scenarios and sample data
│       ├── scenarios/          # E2E test cases
│       └── assets/             # Test images and documents
│
├── docs/poc/                   # POC documentation
├── infra/                      # Docker, PostgreSQL, MinIO configs
├── scripts/                    # Development and validation utilities
└── var/                        # Local storage and logs
```

---

## Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | High-performance async API framework |
| **Pydantic** | Data validation and serialization |
| **SQLAlchemy** | Database ORM |
| **Alembic** | Database migrations |
| **PostgreSQL** | Primary data persistence |

### Frontend
| Technology | Purpose |
|------------|---------|
| **Next.js 14** | React framework with App Router |
| **TypeScript** | Type safety |
| **Tailwind CSS** | Utility-first styling |
| **shadcn/ui** | Component library (local components) |
| **Lucide** | Icon library |

### Infrastructure
| Technology | Purpose |
|------------|---------|
| **Docker Compose** | Local development orchestration |
| **MinIO** | S3-compatible object storage |
| **SSE** | Real-time event streaming |

---

## API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `POST` | `/conversations` | Create a new conversation |
| `GET` | `/conversations/{id}` | Get conversation details |
| `GET` | `/conversations/{id}/messages` | List conversation messages |
| `POST` | `/messages` | Send message (multipart: text + images) |
| `GET` | `/conversations/{id}/events/stream` | SSE event stream |

### Additional Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/conversations` | List recent conversations |
| `POST` | `/runs` | Create a processing run |
| `PATCH` | `/runs/{id}` | Complete a run |
| `GET` | `/reviews` | List pending review tasks |
| `PATCH` | `/reviews/{id}/resolve` | Resolve a review task |

Full API documentation available at `/docs` when running locally.

---

## Configuration

### Environment Variables

Create `apps/api/.env` for backend configuration:

```env
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/multi_agent_bench

# Security (optional for local dev)
API_KEY=poc-dev-key-2026

# Storage (default: local)
STORAGE_PROVIDER=local
# For MinIO:
# STORAGE_PROVIDER=minio
# STORAGE_BUCKET=multi-agent-bench-poc
# STORAGE_ENDPOINT_URL=http://127.0.0.1:9000
# STORAGE_ACCESS_KEY=minioadmin
# STORAGE_SECRET_KEY=minioadmin

# CORS
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:3001
```

Create `apps/web/.env.local` for frontend:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_API_KEY=poc-dev-key-2026
```

---

## Validation

### End-to-End Validation

```bash
python scripts/run_e2e_validation.py
```

### Fixture Scenarios

```bash
python scripts/run_fixture_scenarios.py
```

Available scenarios:
- `faq-question` — Common FAQ query
- `stock-availability` — Stock check request
- `product-image` — Image-based product query
- `document-pdf` — PDF document upload
- `human-review-needed` — Triggers review workflow
- `invalid-attachment` — Tests error handling

---

## Documentation

| Document | Description |
|----------|-------------|
| [HANDOFF.md](docs/poc/HANDOFF.md) | Original POC requirements and context |
| [STRUCTURE.md](docs/poc/STRUCTURE.md) | Detailed project organization |
| [EXECUTION_PLAN.md](docs/poc/EXECUTION_PLAN.md) | Chronological implementation plan |
| [VALIDATION.md](docs/poc/VALIDATION.md) | E2E validation guide |
| [UI.md](docs/poc/UI.md) | Frontend design patterns |
| [AI_EVENTS.md](docs/poc/AI_EVENTS.md) | External AI service integration |
| [PAYLOADS.md](packages/contracts/PAYLOADS.md) | API payload reference |

---

## Future Roadmap

### Architecture Comparison (TCC Focus)

The experimental phase will compare three coordination approaches:

| Architecture | Description |
|--------------|-------------|
| **Centralized Orchestration** | Single orchestrator agent routes all decisions |
| **Structured Workflow** | Predefined pipelines with specialized agents |
| **Decentralized Swarm** | Peer-to-peer agent collaboration |

### Planned Enhancements

- [ ] Real LLM integration (replacing mock runtime)
- [ ] WhatsApp channel adapter
- [ ] Advanced observability dashboard
- [ ] A/B testing infrastructure for architecture comparison
- [ ] Performance metrics and benchmarking

---

## Contributing

This is an academic project. Contributions are welcome for:

- Bug fixes and improvements
- Documentation enhancements
- Test coverage expansion

### Commit Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat(api): add conversation schema
fix(web): handle SSE reconnect
docs(poc): update architecture diagram
```

---

## License

This project is developed as part of an undergraduate thesis (TCC) at [University Name]. All rights reserved.

---

<p align="center">
  <sub>Built with ❤️ for academic research on multi-agent systems</sub>
</p>
