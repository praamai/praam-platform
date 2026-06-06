# praam-platform — shared local dev infrastructure
# Usage: make bootstrap  → first-time setup
#         make            → start stack + verify
#         make help       → list targets

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := up

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
COMPOSE ?= docker compose
GITHUB_ROOT ?= $(abspath $(ROOT)/..)
PRAAM_PLATFORM_API ?= v1
PRAAM_SECRETS_FILE ?= $(HOME)/.praam/secrets.env
LEGACY_RENDER_ENV ?= 0
UV ?= uv
export PRAAM_PLATFORM_ROOT := $(ROOT)
export GITHUB_ROOT
export UV_LINK_MODE ?= copy
export PATH := $(ROOT)/.venv/bin:$(PATH)

.PHONY: help bootstrap install-dev up down wait ps logs doctor render-env render-env-all clean-legacy-env verify-schema clean test check render-env-check config-smoke run-config-api logs-config backup-db sdk sdk-generate sdk-push sdk-check

help: ## Show targets
	@echo "praam-platform $(shell cat $(ROOT)/VERSION 2>/dev/null || echo dev)"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"} {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

bootstrap: ## Create ~/.praam/secrets.env and install dev deps (uv)
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/bootstrap.sh"
	@$(MAKE) install-dev

install-dev: ## uv sync — editable SDK + api/aws extras + dev tools
	@$(UV) sync --all-extras --frozen

up: bootstrap ## Start stack, verify schemas, optional legacy render-env
	@$(COMPOSE) up -d --build
	@$(MAKE) wait
	@$(MAKE) verify-schema
	@$(MAKE) config-smoke
ifneq ($(LEGACY_RENDER_ENV),0)
	@$(MAKE) render-env-all
endif
	@echo ""
	@echo "  praam-platform is up ($(shell cat $(ROOT)/VERSION))."
	@echo "  Postgres      → 127.0.0.1:15430 (praam_dev)"
	@echo "  Redis         → 127.0.0.1:16380"
	@echo "  LiteLLM       → http://127.0.0.1:3100/v1"
	@echo "  Config API    → http://127.0.0.1:3180/v1/apps/<app>/config"
	@echo ""
	@echo "  Apps: PlatformClient('findoc-ai').load()  or  make sdk"
	@echo "  Legacy env:  LEGACY_RENDER_ENV=1 make up"
	@echo "  Stop: make down"
	@echo ""

down: ## Stop platform services
	@$(COMPOSE) down

wait: ## Wait until postgres, redis, litellm, and platform-config are healthy
	@$(MAKE) -f $(ROOT)/make/$(PRAAM_PLATFORM_API)/platform.mk platform-wait

doctor: ## Platform health + wired-app env freshness
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/doctor.sh" $(DOCTOR_FLAGS)

render-env: ## Legacy: render .env.platform.generated (optional APP=findoc-ai)
ifneq ($(strip $(APP)),)
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" "$(APP)"
else
	@$(MAKE) render-env-all
endif

render-env-all: ## Legacy: render .env.platform.generated for every app
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" --all

clean-legacy-env: ## Remove .env.platform.generated from all sibling app repos
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/clean-legacy-env.sh"

verify-schema: ## Verify platform Postgres schemas exist
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/verify-schema.sh"

config-smoke: install-dev ## Verify config API returns all apps (needs running stack for live check)
	@PRAAM_CONFIG_STRICT=1 $(UV) run python "$(ROOT)/scripts/v1/config-smoke.py"

run-config-api: install-dev ## Run platform-config on host :3180 (dev reload)
	@PRAAM_PLATFORM_ROOT="$(ROOT)" PRAAM_SECRETS_FILE="$(PRAAM_SECRETS_FILE)" \
		$(UV) run uvicorn app.main:app --host 127.0.0.1 --port 3180 --reload \
		--app-dir "$(ROOT)/services/platform-config"

ps: ## Show platform container status
	@$(COMPOSE) ps

logs: ## Tail platform logs
	@$(COMPOSE) logs -f

logs-config: ## Tail platform-config logs
	@$(COMPOSE) logs -f platform-config

test: install-dev ## Run unit tests (no Docker required)
	@$(UV) run pytest tests/ -q

check: test render-env-check config-smoke-offline ## Full offline validation

config-smoke-offline: install-dev ## Validate config API via TestClient (no Docker)
	@PRAAM_OFFLINE=1 $(UV) run python "$(ROOT)/scripts/v1/config-smoke.py"

render-env-check: install-dev ## Render all apps to a temp tree (no sibling repos required)
	@tmpdir=$$(mktemp -d); \
	trap 'rm -rf "$$tmpdir"' EXIT; \
	$(UV) run python "$(ROOT)/scripts/v1/_services.py" check-render-all "$(ROOT)" "$$tmpdir"; \
	echo "  render-env-check OK"

clean: down ## Stop services (volumes preserved)

backup-db: ## Dump praam_dev to backups/ (gzip SQL)
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/backup-db.sh"

sdk: sdk-generate sdk-push ## Generate SDK and sync to wired sibling repos

sdk-generate: install-dev ## Bump SDK versions, generate app keys, build TypeScript
	@$(UV) run python "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/sdk.py" generate "$(ROOT)"

sdk-push: ## Copy Python + TypeScript SDK into sibling repos (GITHUB_ROOT/..)
	@$(UV) run python "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/sdk.py" push "$(ROOT)" "$(GITHUB_ROOT)"

sdk-check: install-dev ## Verify sibling repos have current SDK sync manifest
	@$(UV) run python "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/sdk.py" check "$(ROOT)" "$(GITHUB_ROOT)"
