COMPOSE := cd .. && docker compose
IMAGE := hubmi/frontend
changed = ! git diff --quiet $(1) -- $(2) 2>/dev/null
stamp = { git update-ref $(1) HEAD 2>/dev/null || true; }

.PHONY: fmt check build pre-deploy post-deploy dev

fmt:
	bun run fix

check:
	bun run check
	bun run lint

build:
	$(COMPOSE) build frontend

pre-deploy:
	@if $(call changed,refs/deploy/frontend,.) || ! docker image inspect $(IMAGE) >/dev/null 2>&1; then \
		$(MAKE) build && $(call stamp,refs/deploy/frontend); \
	fi

post-deploy:
	@:

dev:
	bun run dev
