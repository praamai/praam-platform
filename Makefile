# praam-platform — shared local dev infrastructure
# Usage: make          → start stack, render env, verify schemas
#         make help    → list targets
#         make down    → stop platform services

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := up

ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
COMPOSE ?= docker compose
GITHUB_ROOT ?= $(abspath $(ROOT)/..)
PRAAM_PLATFORM_API ?= v1
PRAAM_SECRETS_FILE ?= $(HOME)/.praam/secrets.env
export PRAAM_PLATFORM_ROOT := $(ROOT)
export GITHUB_ROOT

.PHONY: help up down wait ps logs doctor render-env render-env-all verify-schema clean

help: ## Show targets
	@echo "praam-platform $(shell cat $(ROOT)/VERSION 2>/dev/null || echo dev)"
	@echo ""
	@grep -E '^[a-zA-Z0-9_-]+:.*?##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?##"} {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

up: ## Start stack, render env for all apps, verify schemas
	@$(COMPOSE) up -d
	@$(MAKE) wait
	@$(MAKE) render-env-all
	@$(MAKE) verify-schema
	@echo ""
	@echo "  praam-platform is up."
	@echo "  Postgres  → 127.0.0.1:15430 (praam_dev)"
	@echo "  Redis     → 127.0.0.1:16380"
	@echo "  LiteLLM   → http://127.0.0.1:3100/v1"
	@echo ""
	@echo "  Next: cd ../findoc-ai && make dev"
	@echo "  Suite: cd ../praam-demo-hub && make all"
	@echo "  Stop:  make down"
	@echo ""

down: ## Stop platform services
	@$(COMPOSE) down

wait: ## Wait until postgres, redis, and litellm are healthy
	@$(MAKE) -f $(ROOT)/make/$(PRAAM_PLATFORM_API)/platform.mk platform-wait

doctor: ## Compare rendered env + check platform health
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/doctor.sh"

render-env: ## Render .env.platform.generated (all apps; optional APP=findoc-ai)
ifneq ($(strip $(APP)),)
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" "$(APP)"
else
	@$(MAKE) render-env-all
endif

render-env-all: ## Render .env.platform.generated for every app in services.yaml
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" --all

verify-schema: ## Verify platform Postgres schemas exist
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/verify-schema.sh"

ps: ## Show platform container status
	@$(COMPOSE) ps

logs: ## Tail platform logs
	@$(COMPOSE) logs -f

clean: down ## Stop services (volumes preserved)
