# praam-platform — shared local dev infrastructure
# Usage: make up | make wait | make render-env | make doctor | make verify-schema

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

.DEFAULT_GOAL := help

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

up: ## Start postgres, redis, litellm on praam-network
	@$(COMPOSE) up -d

down: ## Stop platform services
	@$(COMPOSE) down

wait: ## Wait until postgres, redis, and litellm are healthy
	@$(MAKE) -f $(ROOT)/make/$(PRAAM_PLATFORM_API)/platform.mk platform-wait

doctor: ## Compare rendered env + check platform health
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/doctor.sh"

render-env: ## Render one app: make render-env APP=findoc-ai
	@test -n "$(APP)" || { echo "Usage: make render-env APP=findoc-ai"; exit 1; }
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" "$(APP)"

render-env-all: ## Render .env.platform.generated for every app in services.yaml
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/render-env.sh" --all

verify-schema: ## Verify platform Postgres schemas exist
	@bash "$(ROOT)/scripts/$(PRAAM_PLATFORM_API)/verify-schema.sh"

ps: ## Show platform container status
	@$(COMPOSE) ps

logs: ## Tail platform logs
	@$(COMPOSE) logs -f

clean: down ## Stop services (volumes preserved)
