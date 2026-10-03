COMPOSE := cd .. && docker compose
IMAGE := hubmi/backend
IMAGE_INPUTS := pyproject.toml uv.lock Dockerfile
CODE := src scripts
SERVICES := api
changed = ! git diff --quiet $(1) -- $(2) 2>/dev/null
stamp = { git update-ref $(1) HEAD 2>/dev/null || true; }

.PHONY: fmt check test build pre-deploy post-deploy migrate revision script

fmt:
	uv run ruff format
	uv run ruff check --fix

check:
	uv run ruff format --check
	uv run ruff check
	uv run ty check

test:
	uv run pytest

build:
	$(COMPOSE) build api

pre-deploy:
	@if $(call changed,refs/deploy/backend,$(IMAGE_INPUTS)) || ! docker image inspect $(IMAGE) >/dev/null 2>&1; then \
		$(MAKE) build && $(call stamp,refs/deploy/backend) && $(call stamp,refs/deploy/backend-code); \
	fi
	@$(COMPOSE) config --services | grep -qx postgres && $(COMPOSE) up -d postgres || true
	$(MAKE) migrate

post-deploy:
	@if $(call changed,refs/deploy/backend-code,$(CODE)); then \
		running=$$($(COMPOSE) ps --services --status running | grep -x $(addprefix -e ,$(SERVICES))); \
		[ -z "$$running" ] || $(COMPOSE) restart $$running; \
		$(call stamp,refs/deploy/backend-code); \
	fi

migrate:
	$(COMPOSE) run --rm migrator $(or $(filter-out $@,$(MAKECMDGOALS)),upgrade head)

revision:
	$(COMPOSE) run --rm migrator revision --autogenerate -m "$(m)"

script:
	@$(COMPOSE) run --rm -e AI_BATCH_MODE=1 api scripts.$(word 2,$(MAKECMDGOALS)) $(wordlist 3,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))

%:
	@:
