PARTS := $(patsubst %/Makefile,%,$(wildcard */Makefile))
PROD_HOST ?= personal-main-contabo
PROD_DIR ?= /root/hubmi
BACKUPS ?= backups

.PHONY: env recreate rebuild restart logs down deploy prod prod-logs backup restore fmt check build pre-deploy post-deploy

env:
	@fresh=; test -f .env || { awk 'FNR == 1 && NR > 1 { print "" } 1' .env.example $(addsuffix /.env.example,$(PARTS)) > .env; fresh=1; }; \
	for part in $(PARTS); do \
		override=$$part/docker-compose.override.yml; \
		test -f $$override && continue; \
		cp $$override.example $$override; \
		for port in $$(sed -n 's/.*127\.0\.0\.1:\([0-9]*\):.*/\1/p' $$override | sort -u); do \
			random=$$((20000 + $$(od -An -N2 -tu2 /dev/urandom) % 40000)); \
			sed "s/127\.0\.0\.1:$$port:/127.0.0.1:$$random:/" $$override > $$override.tmp && mv $$override.tmp $$override; \
			test -z "$$fresh" || { sed "s|localhost:$$port/|localhost:$$random/|" .env > .env.tmp && mv .env.tmp .env; }; \
		done; \
	done

recreate:
	docker compose up -d --force-recreate

rebuild: build
	docker compose up -d

restart:
	docker compose restart

logs:
	docker compose logs -f --tail=100

down:
	docker compose down

deploy: pre-deploy
	docker compose up -d
	$(MAKE) post-deploy

prod:
	git fetch origin main
	git bundle create - origin/main | ssh $(PROD_HOST) 'cd $(PROD_DIR) && cat > .git/prod.bundle && git fetch -q .git/prod.bundle refs/remotes/origin/main && rm .git/prod.bundle && git merge -q --ff-only FETCH_HEAD && { make backup || true; } && make deploy && docker exec caddy-caddy-1 caddy reload --config /etc/caddy/Caddyfile && git log -1 --format="deployed %h %s"'

prod-logs:
	ssh -t $(PROD_HOST) 'cd $(PROD_DIR) && docker compose logs -f --tail=100'

backup:
	@mkdir -p $(BACKUPS)
	@f=$(BACKUPS)/hubmi-$$(date -u +%Y%m%dT%H%M%SZ).dump; \
	docker compose exec -T postgres sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" -Fc' > $$f.part \
		&& mv $$f.part $$f && echo $$f || { rm -f $$f.part; exit 1; }
	@ls -1t $(BACKUPS)/hubmi-*.dump | tail -n +31 | xargs -r rm --

restore:
	@test -f "$(file)" || { echo "usage: make restore file=$(BACKUPS)/hubmi-<stamp>.dump"; exit 1; }
	docker compose exec -T postgres sh -c 'pg_restore -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --clean --if-exists --no-owner' < $(file)

fmt check build pre-deploy post-deploy:
	@for part in $(PARTS); do $(MAKE) -C $$part $@ || exit 1; done
