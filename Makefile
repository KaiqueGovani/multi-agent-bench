# ═══════════════════════════════════════════════════════════════════════
# Multi-Agent Bench — Single-command fullstack setup
# Usage:  make up          (first time: infra + deps + migrations + run)
#         make dev         (just start services, assumes setup done)
#         make up DB_PORT=5434 API_PORT=9000   (override any port)
# ═══════════════════════════════════════════════════════════════════════

# ── Ports ─────────────────────────────────────────────────────────────
API_PORT           ?= 8000
RUNTIME_PORT       ?= 8010
WEB_PORT           ?= 3000
DB_PORT            ?= 5433
MINIO_PORT         ?= 9000
MINIO_CONSOLE_PORT ?= 9001

# ── Database ──────────────────────────────────────────────────────────
DB_NAME            ?= multi_agent_bench
DB_USER            ?= postgres
DB_PASSWORD        ?= postgres
DB_URL             := postgresql+psycopg://$(DB_USER):$(DB_PASSWORD)@127.0.0.1:$(DB_PORT)/$(DB_NAME)

# ── Secrets / keys ────────────────────────────────────────────────────
API_KEY            ?= poc-dev-key-2026
AI_SERVICE_SECRET  ?= local-runtime-secret

# ── Compose ───────────────────────────────────────────────────────────
COMPOSE_FILE       ?= infra/docker/docker-compose.yml

# Forward to docker-compose
export DB_PORT DB_NAME DB_USER DB_PASSWORD MINIO_PORT MINIO_CONSOLE_PORT

# ═══════════════════════════════════════════════════════════════════════
.PHONY: up dev setup install sync-env infra db-migrate \
        api runtime web stop infra-down infra-reset infra-logs infra-ps \
        test test-api test-runtime clean test-quality test-quality-report \
        benchmark benchmark-live

# ── One command to rule them all ──────────────────────────────────────
up: infra install sync-env db-migrate dev

# ── Start services (assumes setup done) ──────────────────────────────
dev:
	@echo "Starting API (:$(API_PORT)) · Runtime (:$(RUNTIME_PORT)) · Web (:$(WEB_PORT))"
	@make -j3 api runtime web

# ── Install dependencies ─────────────────────────────────────────────
install:
	cd apps/api && uv sync --all-extras
	cd apps/agent-runtime && uv sync --all-extras
	cd apps/web && npm install

# ── Generate all .env files from Makefile config ─────────────────────
sync-env:
	@echo "Syncing .env files..."
	@echo "APP_ENV=local\n\
DATABASE_URL=$(DB_URL)\n\
LOCAL_STORAGE_PATH=var/storage\n\
STORAGE_PROVIDER=local\n\
STORAGE_BUCKET=multi-agent-bench-poc\n\
RUNTIME_MODE=real\n\
MOCK_RUNTIME_STEP_DELAY_SECONDS=0.2\n\
AI_RUNTIME_URL=http://127.0.0.1:$(RUNTIME_PORT)\n\
AI_RUNTIME_TIMEOUT_SECONDS=20\n\
APP_BASE_URL=http://127.0.0.1:$(API_PORT)\n\
API_KEY=$(API_KEY)\n\
AI_SERVICE_SECRET=$(AI_SERVICE_SECRET)\n\
CORS_ALLOWED_ORIGINS=http://localhost:$(WEB_PORT),http://127.0.0.1:$(WEB_PORT)" > apps/api/.env
	@echo "APP_ENV=local\n\
ENABLE_LIVE_LLM=false\n\
ENABLE_OTEL=false\n\
DEFAULT_ARCHITECTURE_MODE=centralized_orchestration\n\
RUNTIME_MAX_HANDOFFS=6\n\
RUNTIME_TIMEOUT_SECONDS=45\n\
CHAT_API_CALLBACK_TIMEOUT_SECONDS=10" > apps/agent-runtime/.env
	@echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:$(API_PORT)\n\
NEXT_PUBLIC_API_KEY=$(API_KEY)" > apps/web/.env.local
	@rm -rf apps/web/.next
	@echo "  ✓ apps/api/.env"
	@echo "  ✓ apps/agent-runtime/.env"
	@echo "  ✓ apps/web/.env.local"

# ── Docker infrastructure ────────────────────────────────────────────
infra:
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "Postgres :$(DB_PORT) · MinIO :$(MINIO_PORT) · Console :$(MINIO_CONSOLE_PORT)"

infra-down:
	docker compose -f $(COMPOSE_FILE) down

infra-reset:
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) up -d

infra-logs:
	docker compose -f $(COMPOSE_FILE) logs -f

infra-ps:
	docker compose -f $(COMPOSE_FILE) ps

# ── Database migrations ──────────────────────────────────────────────
db-migrate:
	cd apps/api && DATABASE_URL=$(DB_URL) uv run alembic upgrade head

# ── Individual services ──────────────────────────────────────────────
api:
	cd apps/api && uv run uvicorn app.main:app --reload --port $(API_PORT)

runtime:
	cd apps/agent-runtime && uv run uvicorn app.main:app --reload --port $(RUNTIME_PORT)

web:
	cd apps/web && npm run dev -- --port $(WEB_PORT)

# ── Stop everything ──────────────────────────────────────────────────
stop: infra-down

# ── Tests ────────────────────────────────────────────────────────────
test:
	cd apps/api && uv run pytest tests/ -v
	cd apps/agent-runtime && uv run pytest tests/ -v

test-api:
	cd apps/api && uv run pytest tests/ -v

test-runtime:
	cd apps/agent-runtime && uv run pytest tests/ -v

# ── Full cleanup ─────────────────────────────────────────────────────
clean: infra-down
	docker compose -f $(COMPOSE_FILE) down -v
	rm -rf apps/web/node_modules apps/web/.next .venv

# ── E2E Quality Tests ────────────────────────────────────────────────
test-quality:
	cd tests/e2e-quality && uv run pytest -v

test-quality-report:
	cd tests/e2e-quality && uv run pytest -v --html=../../var/reports/quality/report.html

# ── Benchmark (architecture comparison) ───────────────────────────────────────────────────
benchmark:
	python scripts/run_architecture_benchmark.py --architectures cent,work,swarm --iterations 1

benchmark-live:
	python scripts/run_architecture_benchmark.py --architectures cent,work,swarm --iterations 3 --live
