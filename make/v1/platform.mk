# praam-platform v1 API — included by product repos and the platform Makefile.
# Apps pin: -include $(PRAAM_PLATFORM_ROOT)/make/$(PRAAM_PLATFORM_API)/platform.mk

PRAAM_PLATFORM_ROOT ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
PRAAM_PLATFORM_API ?= v1
GITHUB_ROOT ?= $(abspath $(PRAAM_PLATFORM_ROOT)/..)
PRAAM_USE_PLATFORM ?= 1
PRAAM_SECRETS_FILE ?= $(HOME)/.praam/secrets.env

PLATFORM_COMPOSE := docker compose -f $(PRAAM_PLATFORM_ROOT)/docker-compose.yml
PLATFORM_SCRIPTS := $(PRAAM_PLATFORM_ROOT)/scripts/$(PRAAM_PLATFORM_API)

.PHONY: platform-ensure platform-wait platform-doctor render-env verify-schema

platform-ensure: ## Start platform compose stack if PRAAM_USE_PLATFORM=1
	@if [ "$(PRAAM_USE_PLATFORM)" = "0" ]; then \
		echo "PRAAM_USE_PLATFORM=0 — skipping platform-ensure"; \
	else \
		$(PLATFORM_COMPOSE) up -d; \
	fi

platform-wait: ## Wait until postgres, redis, litellm, and platform-config are healthy
	@if [ "$(PRAAM_USE_PLATFORM)" = "0" ]; then \
		echo "PRAAM_USE_PLATFORM=0 — skipping platform-wait"; \
		exit 0; \
	fi
	@echo "Waiting for praam-platform services ..."
	@for i in $$(seq 1 60); do \
		pg_ok=0; redis_ok=0; llm_ok=0; cfg_ok=0; \
		$(PLATFORM_COMPOSE) exec -T postgres pg_isready -U praam -d praam_dev >/dev/null 2>&1 && pg_ok=1; \
		$(PLATFORM_COMPOSE) exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && redis_ok=1; \
		curl -sf http://127.0.0.1:3100/health/liveliness >/dev/null 2>&1 && llm_ok=1; \
		curl -sf http://127.0.0.1:3180/v1/health/live >/dev/null 2>&1 && cfg_ok=1; \
		if [ "$$pg_ok" = "1" ] && [ "$$redis_ok" = "1" ] && [ "$$llm_ok" = "1" ] && [ "$$cfg_ok" = "1" ]; then \
			echo "  OK — postgres, redis, litellm, platform-config"; \
			bash "$(PLATFORM_SCRIPTS)/verify-schema.sh"; \
			exit 0; \
		fi; \
		sleep 2; \
	done; \
	echo "Platform services not ready — run: make -C $(PRAAM_PLATFORM_ROOT) up"; \
	exit 1

platform-doctor: ## Check platform health and rendered env freshness
	@bash "$(PLATFORM_SCRIPTS)/doctor.sh"

render-env: ## Render .env.platform.generated for PRAAM_APP (default: infer from repo)
	@bash "$(PLATFORM_SCRIPTS)/render-env.sh" "$(PRAAM_APP)"

verify-schema: ## Verify expected Postgres schemas exist
	@bash "$(PLATFORM_SCRIPTS)/verify-schema.sh"

platform-sdk: ## Generate SDK and sync to wired sibling repos
	@$(MAKE) -C $(PRAAM_PLATFORM_ROOT) sdk
