COMPOSE := cd .. && docker compose
IMAGE := hubmi/mobile
changed = ! git diff --quiet $(1) -- $(2) 2>/dev/null
stamp = { git update-ref $(1) HEAD 2>/dev/null || true; }

.PHONY: fmt check build pre-deploy post-deploy dev export serve ios

fmt:
	bun run fix

check:
	bun run typecheck
	bun run lint

build:
	$(COMPOSE) build mobile

pre-deploy:
	@if $(call changed,refs/deploy/mobile,.) || ! docker image inspect $(IMAGE) >/dev/null 2>&1; then \
		$(MAKE) build && $(call stamp,refs/deploy/mobile); \
	fi

post-deploy:
	@:

dev:
	bun run web

export:
	bun run export

serve: export
	bun run serve

ios:
	bun run ios
