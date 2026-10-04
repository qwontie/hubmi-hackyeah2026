# HubMi: od wersji demonstracyjnej do produkcji

Instrukcja dla administratora IT, który przejmuje HubMi i uruchamia go produkcyjnie na serwerze ROPS w Krakowie lub Województwa Małopolskiego. Każde polecenie pochodzi z tego repozytorium. Polecenia oznaczone „(sprawdzone lokalnie)” zespół uruchomił 4 października 2026 r. na własnym komputerze z Dockerem; oznaczone „(nie sprawdzone)” opisują krok, którego nie dało się wykonać poza prawdziwym serwerem.

Wersja pokazowa (https://hubmi.qwontie.dev) działa na serwerze zespołu i zawiera dane przykładowe. Produkcja to osobna instalacja na Państwa serwerze, z Państwa domeną, kluczami i kontami.

## 1. Co jest potrzebne

- Serwer z Linuksem (na przykład Debian 12 albo Ubuntu 24.04) z Dockerem i wtyczką Docker Compose v2, `git`, `make`, `openssl`, `curl`.
- Rozmiar: na pilotaż wystarczą 2 vCPU, 4 GB RAM i 40 GB dysku SSD; dla całego województwa zalecamy 4 vCPU, 8 GB RAM i 80 GB. Zmierzone zużycie wersji pokazowej bez ruchu: ok. 230 MB RAM dla wszystkich kontenerów razem. Budowanie obrazów (szczególnie aplikacji mieszkańców) potrzebuje chwilowo ok. 2 GB RAM. Obciążenia przy dużym ruchu nie mierzyliśmy.
- Domena lub subdomena (na przykład `hubmi.malopolska.pl`) z rekordem DNS `A` (i `AAAA`, jeśli serwer ma IPv6) wskazującym serwer.
- Otwarte porty 80 i 443 (TCP oraz 443 UDP dla HTTP/3). Certyfikat TLS Caddy pobiera sam z Let's Encrypt.
- Konto Google Cloud z płatnym kluczem Gemini API (punkt 7).
- Konto u dostawcy poczty Resend i możliwość dodania rekordów DNS dla domeny nadawcy (punkt 6).

Architektura:

```
Internet ──443──> Caddy (caddy/)
                    ├── /api/*   -> api       (backend/, FastAPI, port 8080)
                    ├── /admin*  -> frontend  (frontend/, panel ROPS, port 3000)
                    └── /        -> mobile    (mobile/, aplikacja mieszkańców, web, port 3000)
                  api ──> postgres (PostgreSQL 17 z pgvector, sieć wewnętrzna)
                  api ──> Google Gemini API, Resend API, rops.krakow.pl (wyjście HTTPS)
```

Caddy łączy się z usługami przez zewnętrzną sieć Dockera `caddy`; nazwy `hubmi-api`, `hubmi-frontend` i `hubmi-mobile` nadają pliki `*/docker-compose.override.yml`. Baza nie jest dostępna z zewnątrz.

## 2. Pobranie kodu i plik `.env`

```sh
sudo mkdir -p /opt/hubmi && sudo chown "$USER" /opt/hubmi
git clone <adres-repozytorium> /opt/hubmi
cd /opt/hubmi
docker network create caddy
make env
chmod 600 .env
```

`make env` (sprawdzone lokalnie) skleja `.env.example`, `backend/.env.example`, `frontend/.env.example` i `mobile/.env.example` w jeden plik `.env` oraz tworzy `backend/`, `frontend/` i `mobile/docker-compose.override.yml` z losowymi portami przypiętymi do 127.0.0.1. Pliki `.env` i `docker-compose.override.yml` nie trafiają do gita.

Sekrety generuj tak (każdy osobno):

```sh
openssl rand -hex 32
```

Używaj znaków szesnastkowych: hasło bazy trafia do adresu połączenia, więc znaki takie jak `@`, `/` czy `:` by go zepsuły.

### Zmienne w `.env`

Wymagane, bez nich produkcja nie działa:

| Zmienna | Co ustawić | Co się stanie bez niej |
|---|---|---|
| `AUTH__SECRET` | wynik `openssl rand -hex 32` | API nie wystartuje (minimum 32 znaki). Podpisuje sesje, linki do rozmów z mieszkańcami, wolontariuszami i ekspertami oraz skróty adresów IP. Zmiana unieważnia wszystkie sesje i wszystkie wysłane linki, więc ustaw raz i nie zmieniaj bez potrzeby |
| `DB__PASSWORD` | wynik `openssl rand -hex 32` | API nie wystartuje (minimum 16 znaków, inne niż użytkownik i nazwa bazy). Ustaw przed pierwszym startem: Postgres zapisuje hasło przy pierwszym utworzeniu bazy |
| `MAILER__PUBLIC_URL` | pełny adres produkcyjny, np. `https://hubmi.malopolska.pl` | logowanie do panelu i wszystkie formularze kończą się błędem 403 (API przyjmuje żądania zmieniające dane tylko z tego adresu), a linki w e-mailach prowadzą do wersji pokazowej |
| `LLM__GEMINI_API_KEY` | klucz z punktu 7 | wyszukiwanie działa tylko po słowach, asystenci AI są niedostępni, import treści z ROPS nie działa |
| `MAILER__RESEND_API_KEY` | klucz z punktu 6 | żadne e-maile nie wychodzą (odpowiedzi ROPS, linki do rozmów, powiadomienia) |
| `MAILER__SENDER` | np. `HubMi ROPS <hubmi@malopolska.pl>` | domyślny nadawca wskazuje domenę zespołu i Resend odrzuci wysyłkę z Państwa konta |

Zalecane:

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `MAILER__STAFF_EMAIL` | puste | skrzynka ROPS na powiadomienia o nowych zgłoszeniach; puste wyłącza te powiadomienia |
| `MAILER__STAFF_DIGEST_SECONDS` | `600` | co ile sekund zbierać powiadomienia dla ROPS w jeden e-mail |
| `MAILER__REPLY_TO` | puste | adres, na który trafią odpowiedzi na e-maile z systemu |
| `LLM__DAILY_BUDGET_USD` | `5` | limit wydatków na AI z działań ludzi w ciągu ostatnich 24 godzin |
| `LLM__BATCH_DAILY_BUDGET_USD` | `8` | osobny limit dla importów i skryptów |
| `AUTH__SESSION_HOURS` | `12` | jak długo ważna jest sesja pracownika w panelu |
| `TZ` | `UTC` | strefa czasowa kontenerów i logów; można ustawić `Europe/Warsaw` |

Techniczne, zostaw jak są, chyba że wiesz, po co je zmieniasz:

| Zmienna | Domyślnie | Znaczenie |
|---|---|---|
| `COMPOSE_FILE`, `COMPOSE_PROFILES` | z `.env.example` | które pliki i usługi uruchamia `docker compose` |
| `RUN_ENVIRONMENT` | `prod` | tryb produkcyjny (kontenery i tak ustawiają `prod`) |
| `DB__HOST`, `DB__PORT`, `DB__USER`, `DB__DB_NAME` | `postgres`, `5432`, `hubmi`, `hubmi` | połączenie z bazą w kontenerze |
| `DB__MIN_POOL_SIZE`, `DB__MAX_POOL_SIZE` | `5`, `20` | pula połączeń z bazą |
| `DB__SCRIPTS_CONNECTION_URL` | adres do `localhost` | tylko dla skryptów uruchamianych poza Dockerem, na produkcji nieużywane |
| `API__HOST`, `API__PORT` | `0.0.0.0`, `8080` | adres API w kontenerze |
| `API__WORKERS` | `1` | **musi zostać 1**: limity zapytań, pamięć podręczna wyszukiwania i harmonogram importu działają w jednym procesie |
| `API__DOCS` | `false` | `true` włącza dokumentację API pod `/api/docs`; na produkcji zostaw `false` |
| `LOG__LEVEL`, `LOG__LEVEL_EXTERNAL`, `LOG__SHOW_TIME`, `LOG__CONSOLE_WIDTH` | `INFO`, `WARNING`, `false`, `150` | poziom i format logów |
| `LLM__MODEL` | `google-gla:gemini-2.5-flash` | model językowy |
| `SCHEDULE__ENABLED`, `SCHEDULE__AT`, `SCHEDULE__TIMEZONE` | `true`, `03:30`, `Europe/Warsaw` | codzienny import z rops.krakow.pl (punkt 5) |
| `PUBLIC_API_BASE_URL` | `/api` | adres API dla panelu ROPS |
| `ALLOWED_HOSTS` | puste | tylko dla trybu deweloperskiego panelu |
| `EXPO_PUBLIC_API_URL` | adres wersji pokazowej | tylko dla aplikacji natywnej na telefon (punkt 10); wersja web używa własnego adresu |

Proxy ma osobny plik `caddy/.env`:

```sh
cd /opt/hubmi/caddy
cp Caddyfile.example Caddyfile
cp .env.example .env
```

W `caddy/.env` ustaw `HUBMI_DOMAIN=hubmi.malopolska.pl` (bez `https://`). `CLOUDFLARE_API_TOKEN` zostaw pusty, chyba że serwer stoi za Cloudflare (punkt 8).

## 3. Pierwsze uruchomienie

```sh
cd /opt/hubmi
make deploy
```

`make deploy` (sprawdzone lokalnie) buduje obrazy, uruchamia Postgresa, wykonuje migracje bazy (`alembic upgrade head` w kontenerze `migrator`) i uruchamia `api`, `frontend` i `mobile`. Kolejne `make deploy` przebudowują tylko to, co się zmieniło.

Proxy:

```sh
cd /opt/hubmi/caddy
docker compose up -d
```

Kontrola (sprawdzone lokalnie, poza adresem domeny):

```sh
cd /opt/hubmi
docker compose ps
curl -s https://hubmi.malopolska.pl/api/health
curl -s https://hubmi.malopolska.pl/api/meta
```

Oczekiwane: cztery usługi `Up` (postgres `healthy`), `{"ok":true}` i `{"demo":false}`. Pierwsze pobranie certyfikatu trwa do minuty; błędy TLS widać w `docker compose logs caddy` w katalogu `caddy/`. Zapytania przez domenę: nie sprawdzone.

Pierwsze konto pracownika ROPS:

```sh
make -C backend script user.create -- <login> '<hasło>' --role admin
```

(sprawdzone lokalnie). Separator `--` jest potrzebny, bo `make` inaczej potraktuje `--role` jako własną opcję. Hasło ze znakami `=` lub `:` lepiej podać bezpośrednio przez Docker:

```sh
docker compose run --rm api scripts.user.create <login> '<hasło>' --role admin
```

Panel: `https://hubmi.malopolska.pl/admin`. To samo polecenie z istniejącym loginem ustawia nowe hasło i wylogowuje wszystkie sesje tego konta. Konto eksperta: `--role expert --name "Imię Nazwisko" --expertise "dziedzina" --email adres`. Usunięcie konta: `make -C backend script user.delete <login>`.

## 4. Pozostawienie wersji demonstracyjnej

Są dwie drogi. Wybierz jedną.

**A. Czysta baza (zalecane).** Nowa instalacja z punktu 3 ma pustą bazę bez żadnych danych przykładowych. Treści z ROPS wczytaj według punktu 5. Kroków poniżej nie potrzebujesz poza kontrolą `/api/meta`.

**B. Przeniesienie bazy z wersji pokazowej.** Zachowuje bibliotekę z obrazkami, wyzwania, materiały i ręczne poprawki z panelu. Zespół przekazuje plik kopii (`make backup` na serwerze pokazowym tworzy `backups/hubmi-<data>.dump`). Na nowym serwerze, po punkcie 3:

```sh
cd /opt/hubmi
mkdir -p backups && cp /sciezka/do/hubmi-<data>.dump backups/
make restore file=backups/hubmi-<data>.dump
make -C backend script demo.wipe
curl -s https://hubmi.malopolska.pl/api/meta
make -C backend script demo.purge_tests
make -C backend script demo.purge_tests -- --apply
make -C backend script grants.demo_call -- --wipe
```

- `make restore` (sprawdzone lokalnie) wczytuje kopię do działającej bazy i nadpisuje jej zawartość.
- `demo.wipe` (sprawdzone lokalnie na pustej bazie) usuwa wszystkie wiersze zapisane przez skrypt danych przykładowych. Potem `/api/meta` musi zwrócić `{"demo":false}`, a panel i aplikacja przestają pokazywać informację o danych przykładowych.
- `demo.purge_tests` bez `--apply` tylko pokazuje tabelę tego, co usunie; z `--apply` usuwa wszystko, co wpisali ludzie podczas hackathonu i testów (zgłoszenia, pomysły, wnioski, wolontariuszy, subskrypcje, dzienniki wyszukiwań). Biblioteka, wyzwania i materiały zostają. **Uruchom go tylko teraz, przed startem. Na działającej produkcji usunąłby prawdziwe zgłoszenia mieszkańców.** (sprawdzone lokalnie na pustej bazie)
- `grants.demo_call -- --wipe` usuwa pokazowy nabór i wnioski do niego (nie sprawdzone).

Konta pracowników z wersji pokazowej usuń i załóż własne:

```sh
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select login, role from admin_user"'
make -C backend script user.delete <login>
```

(sprawdzone lokalnie). Nowy serwer ma własny `AUTH__SECRET`, więc sesje i linki wysłane w wersji pokazowej przestają działać same.

## 5. Treści z ROPS

Pierwszy import (wymaga klucza Gemini; przy drodze B nie jest potrzebny, ale niczego nie psuje):

```sh
make -C backend script library.import_rops
make -C backend script library.images
make -C backend script knowledge.import_rops
```

- `library.import_rops` wczytuje Bibliotekę Innowacji Społecznych z rops.krakow.pl (w wersji pokazowej 115 pozycji i 9 kategorii) i liczy wektory do wyszukiwania. Jest idempotentny: ponowne uruchomienie aktualizuje zmienione pozycje i nie nadpisuje tych, które pracownik poprawił w panelu.
- `library.images` daje każdej innowacji jeden obrazek: zdjęcie z jej broszury ROPS albo kadr z filmu (jedno tanie wywołanie AI na kandydata), a gdy go brak, kopię pasującego obrazka z puli już przypisanych. Niczego nie generuje. Opcje: `--slug <slug> --force` ponawia jedną pozycję.
- `knowledge.import_rops` wczytuje raporty, publikacje i poradniki ROPS, wyciąga z nich wyzwania regionu z cytatem i stroną źródła oraz dane powiatów. Pierwsze uruchomienie trwa ok. 30 minut i kosztuje ok. 0,5 USD, kolejne kilka minut.

Polecenia importu nie były uruchamiane przy pisaniu tej instrukcji (nie sprawdzone tutaj; na serwerze pokazowym działają od 3 października).

Codzienny import: API samo uruchamia oba importy raz dziennie o `SCHEDULE__AT` (domyślnie 03:30 czasu polskiego), a gdy było wtedy wyłączone, nadrabia po starcie. Niezmienione strony i pliki nie kosztują nic. Nowe innowacje dostają obrazek z puli. Wyłączenie: `SCHEDULE__ENABLED=false` w `.env` i `docker compose up -d`. Podgląd:

```sh
docker compose logs api | grep "schedule:"
```

(sprawdzone lokalnie: wpis `schedule: daily import at 03:30 Europe/Warsaw`). Import z panelu: Biblioteka i Wiedza mają własne przyciski importu, a pojedynczą innowację dodaje się linkiem do strony ROPS.

Wyzwania regionu i materiały pracownicy ROPS sprawdzają i poprawiają w panelu (Wiedza). Własny materiał dodaje się linkiem, plikiem PDF albo tekstem; streszczenie robi AI.

Import zależy od budowy stron rops.krakow.pl. Jeśli ROPS przebuduje swoją stronę, import zacznie zgłaszać błędy (`failed` w logu) i będzie wymagał zmiany w `backend/src/services/ingest/` lub `backend/src/services/knowledge/`.

## 6. Poczta

HubMi wysyła e-maile przez API Resend (`backend/src/services/mail/sender.py`). Inny dostawca, na przykład serwer pocztowy urzędu, wymaga podmiany tego modułu w kodzie.

1. Załóż konto w Resend i dodaj domenę nadawcy (najlepiej subdomenę, np. `powiadomienia.malopolska.pl`).
2. Dodaj w DNS rekordy, które poda Resend: SPF (`TXT`), DKIM (`TXT`) oraz rekord `MX` dla zwrotów. Dodaj też DMARC, np. `_dmarc` `TXT` `v=DMARC1; p=quarantine`.
3. Gdy Resend pokaże domenę jako zweryfikowaną, utwórz klucz API z prawem wysyłki i wpisz go do `MAILER__RESEND_API_KEY`.
4. Ustaw `MAILER__SENDER` na adres w tej domenie, `MAILER__STAFF_EMAIL` na skrzynkę zespołu ROPS, opcjonalnie `MAILER__REPLY_TO`.
5. `docker compose up -d`, żeby API wczytało zmiany.
6. Test dostarczenia: w aplikacji mieszkańców zgłoś problem z własnym adresem i zgodą, w panelu odpowiedz na to zgłoszenie. Powinny przyjść: powiadomienie na `MAILER__STAFF_EMAIL` (po czasie z `MAILER__STAFF_DIGEST_SECONDS`) i odpowiedź z linkiem do rozmowy. Sprawdź nagłówki: `spf=pass`, `dkim=pass`. Potem usuń zgłoszenie testowe (punkt 9, przycisk usunięcia danych kontaktowych) (nie sprawdzone).

Logi aplikacji maskują adresy e-mail. Wysyłka bez klucza jest pomijana, a reszta aplikacji działa.

## 7. AI (Google Gemini)

1. W Google Cloud utwórz projekt z włączonymi płatnościami i klucz Gemini API (Google AI Studio, „Get API key”, dla tego projektu). Na planie płatnym Google według swoich warunków nie używa treści zapytań do ulepszania produktów; na darmowym używa, więc darmowy klucz nie nadaje się na produkcję.
2. Wpisz klucz do `LLM__GEMINI_API_KEY` i `docker compose up -d`.
3. W Google Cloud Billing ustaw alert budżetowy na projekt.

Używane modele: `gemini-2.5-flash` (teksty), `gemini-embedding-001` (wektory), model obrazowy Gemini do ilustracji pomysłów w Kreatorze. Adresy e-mail nigdy nie trafiają do AI.

Limity wydatków: każde wywołanie najpierw sprawdza sumę z ostatnich 24 godzin w tabeli `ai_call`. `LLM__DAILY_BUDGET_USD` dotyczy działań ludzi, `LLM__BATCH_DAILY_BUDGET_USD` importów i skryptów. Zmiana: nowa wartość w `.env` i `docker compose up -d`. Ceny modeli są wpisane w `backend/src/services/ai/costs.py`; gdy Google je zmieni, trzeba je tam poprawić. Wydatki z ostatniej doby (sprawdzone lokalnie):

```sh
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "select scope, count(*), round(sum(cost_usd)::numeric, 4) as usd from ai_call where created_at > now() - interval '"'"'1 day'"'"' group by scope"'
```

Koszty zmierzone w wersji pokazowej: wyszukiwanie ok. 0,0017 USD, zgłoszenie problemu ok. 0,0003 USD, ilustracja pomysłu ok. 0,09 USD (szacunek).

Gdy model nie odpowiada albo limit się wyczerpał: wyszukiwanie działa dalej na samych słowach, zgłoszenia zapisują się, a tytuł i grupę dostają później (API ponawia co 5 minut), asystenci w Kreatorze, Middlemanie i panelu pokazują, że AI jest chwilowo niedostępne.

## 8. Bezpieczeństwo i utrzymanie

**Sekrety.** Tylko w `/opt/hubmi/.env` i `caddy/.env` z prawami `600`, nigdy w gicie ani w zgłoszeniach. Klucze Gemini i Resend można w każdej chwili wymienić u dostawcy i w `.env`. `AUTH__SECRET` zmieniaj tylko świadomie (punkt 2).

**Zapora.** Z zewnątrz otwarte tylko 80, 443 i SSH (najlepiej tylko z sieci urzędu). Porty z `*/docker-compose.override.yml` są przypięte do 127.0.0.1 i tak musi zostać: API ufa nagłówkowi `X-Forwarded-For`, który ustawia Caddy.

**Adres IP klienta.** Caddy przekazuje do API prawdziwy adres klienta (`header_up X-Forwarded-For {client_ip}` w `caddy/site.caddy`). `Caddyfile.example` zakłada, że przed serwerem może stać Cloudflare (`trusted_proxies cloudflare`). Bez Cloudflare blok `servers { ... }` w `caddy/Caddyfile` niczego nie zmienia i można go usunąć. Gdy przed serwerem stoi inny serwer pośredniczący urzędu, ustaw w nim `trusted_proxies static <adresy-tego-serwera>` i `client_ip_headers X-Forwarded-For`. Inaczej wszyscy mieszkańcy dzielą jeden limit zapytań. Przy Cloudflare z certyfikatem przez DNS dopisz w bloku globalnym `acme_dns cloudflare {env.CLOUDFLARE_API_TOKEN}` i ustaw token w `caddy/.env` (nie sprawdzone). Adres do powiadomień Let's Encrypt: `email admin@malopolska.pl` w bloku globalnym.

**Sesje.** Konta mają tylko pracownicy ROPS i eksperci. Ciasteczko `hubmi_session` jest `httpOnly`, `Secure`, `SameSite=Lax`, ważne `AUTH__SESSION_HOURS` godzin. Wylogowanie unieważnia tę jedną sesję, zmiana hasła wszystkie. Próby logowania są ograniczane i liczone w bazie. Drugiego składnika logowania nie ma.

**Limity zapytań.** Wpisane w kodzie przy endpointach (`backend/src/api/limits.py` i routery w `backend/src/api/routers/`), liczone po skrócie HMAC adresu IP. Zmiana wartości wymaga zmiany kodu.

**Nagłówki.** `caddy/site.caddy` ustawia HSTS, `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`, `Permissions-Policy` i osobne Content-Security-Policy dla API, panelu i aplikacji. CSP dopuszcza obrazki z rops.krakow.pl i filmy z YouTube (wczytywane dopiero po kliknięciu). Po zmianie `site.caddy`: `docker compose exec caddy caddy reload --config /etc/caddy/Caddyfile` w katalogu `caddy/`.

**Kopie bazy.**

```sh
cd /opt/hubmi
make backup
make restore file=backups/hubmi-<data>.dump
```

(oba sprawdzone lokalnie). `make backup` robi `pg_dump -Fc` do `backups/hubmi-<czas UTC>.dump` i trzyma 30 najnowszych. `make restore` nadpisuje bieżącą bazę, więc najpierw zrób świeżą kopię. Kopia co noc z crona (`crontab -e`, nie sprawdzone):

```
30 2 * * * cd /opt/hubmi && make backup >> /var/log/hubmi-backup.log 2>&1
```

Kopie leżą na tym samym serwerze: kopiuj je także poza serwer (na przykład `rsync` na serwer kopii urzędu) i raz na kwartał sprawdzaj odtworzenie na osobnej maszynie. Obrazki innowacji są w bazie, więc kopia bazy obejmuje całą treść.

**Aktualizacje i wycofanie.**

```sh
cd /opt/hubmi
make backup
git pull --ff-only
make deploy
```

Migracje wykonują się same w `make deploy`. Wycofanie: `git checkout <poprzedni-commit>`, `make restore file=<kopia sprzed aktualizacji>`, `make deploy` (nie sprawdzone). Aktualizacje obrazów bazowych i zależności przychodzą przez zmiany w repozytorium (`uv.lock`, `bun.lock`); system serwera aktualizuj osobno. Cele `make prod` i `make prod-logs` w `Makefile` obsługują serwer pokazowy zespołu i na produkcji nie są potrzebne.

**Logi.**

```sh
cd /opt/hubmi
make logs
docker compose logs api --since 24h | grep -E "ERROR|schedule:|budget"
```

Warto obserwować: odpowiedź `/api/health` (monitoring co minutę, `503` oznacza brak bazy), błędy w logu API, wynik nocnego importu (`schedule: library import ...`, `failed=`), dzienne wydatki AI, wolne miejsce na dysku i datę ostatniej kopii. Logi kontenerów zawierają adresy IP i adresy stron (bez treści formularzy). Ogranicz ich rozmiar w `/etc/docker/daemon.json`, potem `systemctl restart docker` (nie sprawdzone):

```json
{ "log-driver": "json-file", "log-opts": { "max-size": "20m", "max-file": "5" } }
```

## 9. Ochrona danych przed uruchomieniem

Co już robi produkt:

- Bez formularza nie ma danych osobowych. Mieszkańcy nie mają kont ani ciasteczek; wracają do swoich spraw przez link z tokenem.
- Adres e-mail tylko ze zgodą, zapisaną z czasem udzielenia. Tekstu wyszukiwania nie zapisujemy, adresy IP tylko jako skrót HMAC.
- Do AI nie trafiają adresy e-mail. Logi maskują adresy e-mail.
- Usunięcie danych osoby na żądanie: w panelu Opinie, karta kontaktu, „Prośba o usunięcie danych”, „Usuń dane kontaktowe”. Czyści adres i zgodę we wszystkich sprawach, usuwa zgłoszenia wolontariusza i subskrypcje; w dzienniku zostają tylko liczby. Nie przeszukuje tekstu, który osoba sama wpisała do opisu.
- Wzór strony prywatności pod `/prywatnosc` (`mobile/src/app/prywatnosc.tsx`) i notka pod każdym formularzem (`mobile/src/features/privacy-note.tsx`).

Praca organizacyjna, której produkt nie zrobi:

- [ ] Administrator danych: ROPS w Krakowie, wpis w rejestrze czynności przetwarzania (art. 30 RODO).
- [ ] Umowy powierzenia (art. 28): hosting, Google (Gemini API; dla danych w UE rozważyć Vertex AI w regionie UE, co wymaga zmian w kodzie), dostawca poczty, CDN, jeśli jest. Dla firm spoza UE podstawa przekazania (Data Privacy Framework albo standardowe klauzule umowne).
- [ ] Ocena skutków (DPIA, art. 35): opisy problemów społecznych mogą zawierać dane o zdrowiu, przemocy czy ubóstwie, także osób trzecich. Do tego decyzja o podstawie dla danych szczególnych kategorii (art. 9) i nowe brzmienie zgód.
- [ ] Własny tekst polityki prywatności i klauzuli informacyjnej (art. 13) z danymi inspektora ochrony danych, wpisany w `mobile/src/app/prywatnosc.tsx`.
- [ ] Okresy przechowywania. Dziś nic nie usuwa się samo; potrzebne jest zadanie nocne według okresów ustalonych przez ROPS (nie istnieje), także dla logów i kopii.
- [ ] Procedura obsługi żądań osób (dostęp, sprostowanie, usunięcie), łącznie z usuwaniem z kopii zapasowych.
- [ ] Imienne konta pracowników z silnymi hasłami.

## 10. Aplikacja mobilna

Co istnieje: aplikacja mieszkańców w `mobile/` (React Native z Expo). Na produkcji działa jej wersja web, serwowana pod `/` przez kontener `mobile` i działająca w każdej przeglądarce telefonu. Wersję natywną na iOS zespół zbudował lokalnie na Macu z Xcode (`bunx expo prebuild -p ios`, potem `xcodebuild`) i zainstalował na własnym telefonie. Wersji na Androida nie budowaliśmy.

Do publikacji w sklepach potrzebne są (nie sprawdzone):

- konto Apple Developer Program organizacji i konto Google Play Console organizacji;
- własny identyfikator aplikacji w `mobile/app.json` (`ios.bundleIdentifier`, `android.package`; dziś to identyfikator zespołu);
- `EXPO_PUBLIC_API_URL=https://hubmi.malopolska.pl` w `mobile/.env` przed budowaniem, inaczej aplikacja łączy się z wersją pokazową;
- podpisane buildy (Xcode albo usługa EAS Build), opisy, zrzuty ekranu, informacje o prywatności w App Store i formularz bezpieczeństwa danych w Google Play, przegląd przez sklepy.

## 11. Ograniczenia prototypu

- Jedna instancja API (`API__WORKERS=1`): limity, pamięć podręczna i harmonogram są w pamięci procesu. Skalowanie w poziomie wymaga zmian w kodzie.
- Brak drugiego składnika logowania i brak resetu hasła przez e-mail (hasło ustawia administrator poleceniem `user.create`).
- Brak automatycznego usuwania starych danych (punkt 9).
- Poczta tylko przez Resend, AI tylko przez Gemini API.
- Import zależy od budowy stron rops.krakow.pl.
- Testy automatyczne obejmują wybrane części API (`make -C backend test`), nie całość; testów obciążeniowych nie było.
- Jakość wyszukiwania sprawdzaliśmy na niewielkim zestawie przykładowych opisów.
- Kod powstał w 24 godziny z pomocą agentów AI; przed produkcją zalecamy przegląd bezpieczeństwa.

## 12. Lista kontrolna przed startem

1. Serwer, domena, DNS i porty 80/443 gotowe; `curl -s https://<domena>/api/health` zwraca `{"ok":true}`.
2. `.env` z nowymi `AUTH__SECRET` i `DB__PASSWORD`, prawa `600`.
3. `MAILER__PUBLIC_URL` to adres produkcyjny; logowanie do `/admin` działa.
4. `/api/meta` zwraca `{"demo":false}`; nie ma danych testowych ani kont z wersji pokazowej.
5. Konta pracowników ROPS założone, imienne.
6. Biblioteka, obrazki, wyzwania i materiały wczytane; nocny import widoczny w logu.
7. Domena nadawcy zweryfikowana (SPF, DKIM), test e-maila przeszedł, `MAILER__STAFF_EMAIL` ustawiony.
8. Płatny klucz Gemini, limity dzienne ustawione, alert budżetowy w Google Cloud.
9. Kopia nocna w cronie, kopia poza serwerem, odtworzenie sprawdzone.
10. Umowy powierzenia, DPIA, polityka prywatności i okresy przechowywania zatwierdzone przez inspektora ochrony danych ROPS.
