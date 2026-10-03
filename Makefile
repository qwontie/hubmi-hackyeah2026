PARTS := $(patsubst %/Makefile,%,$(wildcard */Makefile))

.PHONY: env recreate rebuild restart logs down deploy fmt check build pre-deploy post-deploy

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

fmt check build pre-deploy post-deploy:
	@for part in $(PARTS); do $(MAKE) -C $$part $@ || exit 1; done
